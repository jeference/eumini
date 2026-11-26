"""Teste dos prompts por categoria no estilo único (o antigo "pixar").

Usa o prompt de produção (`apps/backend/catalog/prompts.py`). Uso, a partir da raiz:
    apps/backend/.venv/Scripts/python.exe -I docs/prompts/teste_prompts.py <rodada> [id ...]

Gera uma imagem por caso de `casos.json` na Runware, como o worker faz (modelo principal e,
se falhar, o reserva), classifica a imagem gerada com o Jev e grava em
`docs/prompts/resultados/<rodada>/` as imagens, `resultado.json` e `folha.jpg`.
"""

import base64
import io
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "apps/backend"))
sys.path.insert(0, str(RAIZ / "docs/classificador"))

from catalog import prompts as P  # noqa: E402  (módulo sem Django)
import teste_jev  # noqa: E402

RUNWARE_URL = "https://api.runware.ai/v1"
TAMANHO = 1024

# --- Prompt --------------------------------------------------------------------------------
# A rodada usa o prompt de produção (`catalog/prompts.py`). O texto exato de cada rodada
# anterior (r0 a r3) fica em `resultados/<rodada>/resultado.json`, no campo `prompt`.


def prompt_da_rodada(categoria: str) -> str:
    return P.photo_prompt(category=categoria)


# --- Runware ----------------------------------------------------------------------------


def env() -> dict:
    valores = {}
    for linha in (RAIZ / "apps/backend/.env").read_text(encoding="utf-8").splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            k, v = linha.split("=", 1)
            valores[k.strip()] = v.strip().strip("\"'")
    return valores


ENV = env()
MODELOS = (
    ENV.get("RUNWARE_IMAGE_MODEL") or "openai:gpt-image@2",
    ENV.get("RUNWARE_IMAGE_FALLBACK_MODEL") or "google:4@2",
)


def gerar(foto: bytes, prompt: str, modelo: str) -> tuple[bytes, float | None]:
    tarefa = {
        "taskType": "imageInference",
        "taskUUID": str(uuid.uuid4()),
        "model": modelo,
        "positivePrompt": prompt,
        "width": TAMANHO,
        "height": TAMANHO,
        "numberResults": 1,
        "outputType": "dataURI",
        "outputFormat": "PNG",
        "includeCost": True,
        "inputs": {"referenceImages": ["data:image/png;base64," + base64.b64encode(foto).decode()]},
    }
    r = requests.post(
        RUNWARE_URL,
        json=[tarefa],
        headers={"Authorization": f"Bearer {ENV['RUNWARE_API_KEY']}"},
        timeout=180,
    )
    corpo = r.json()
    if corpo.get("errors") or corpo.get("error") or r.status_code >= 400:
        raise RuntimeError(json.dumps(corpo.get("errors") or corpo.get("error") or r.status_code)[:300])
    item = next(d for d in corpo["data"] if d.get("imageDataURI"))
    return base64.b64decode(item["imageDataURI"].partition(",")[2]), item.get("cost")


def foto_png(arquivo: Path) -> bytes:
    """Normaliza como o backend: RGB, até 1024 px, PNG."""
    im = Image.open(arquivo).convert("RGB")
    im.thumbnail((TAMANHO, TAMANHO))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def rodar_caso(rodada: str, caso: dict, pasta: Path, sessao_jev: requests.Session) -> dict:
    prompt = prompt_da_rodada(caso["categoria"])
    foto = foto_png(BASE / caso["arquivo"])
    resultado = {"id": caso["id"], "categoria": caso["categoria"], "prompt": prompt, "tentativas": []}
    t0 = time.monotonic()
    for modelo in MODELOS:
        for espera in (0, 15, 30, 60):
            time.sleep(espera)
            try:
                imagem, custo = gerar(foto, prompt, modelo)
                erro = None
                break
            except Exception as exc:  # noqa: BLE001
                erro = str(exc)
                # Saldo reservado por chamadas em andamento: esperar não é falha do modelo.
                if "concurrentRequestLimitExceeded" not in erro:
                    break
        if erro:
            resultado["tentativas"].append({"modelo": modelo, "erro": erro})
            continue
        resultado.update(modelo=modelo, custo_usd=custo)
        destino = pasta / f"{caso['id']}.jpg"
        Image.open(io.BytesIO(imagem)).convert("RGB").save(destino, "JPEG", quality=88)
        jev = teste_jev.chamar(sessao_jev, "jev-1.14.0", {"tipo": "versao", "arquivo": str(destino)})
        resultado["jev"] = jev.get("decisao", f"erro {jev.get('erro')}")
        resultado["jev_personagem"] = (jev.get("respostas") or {}).get("character", {}).get("noul")
        resultado["categoria_mantida"] = resultado["jev"] == caso["categoria"]
        break
    resultado["segundos"] = round(time.monotonic() - t0, 1)
    marca = "ok " if resultado.get("categoria_mantida") else "ERR"
    print(f"{marca} {caso['id']:<26} {resultado.get('modelo', 'falhou'):<20} jev={resultado.get('jev')}")
    return resultado


def folha(pasta: Path, casos: list[dict], resultados: list[dict]) -> None:
    lado, cols = 300, 4
    pares = len(casos)
    linhas = (pares + cols - 1) // cols
    img = Image.new("RGB", (cols * lado * 2, linhas * (lado + 28)), "white")
    d = ImageDraw.Draw(img)
    por_id = {r["id"]: r for r in resultados}
    for i, caso in enumerate(casos):
        x, y = (i % cols) * lado * 2, (i // cols) * (lado + 28)
        for j, arquivo in enumerate((BASE / caso["arquivo"], pasta / f"{caso['id']}.jpg")):
            if arquivo.exists():
                im = Image.open(arquivo).convert("RGB")
                im.thumbnail((lado - 6, lado - 6))
                img.paste(im, (x + j * lado + (lado - im.width) // 2, y + 26))
        r = por_id.get(caso["id"], {})
        rotulo = f"{caso['id']}  jev={r.get('jev', '-')}"
        d.text((x + 6, y + 6), rotulo, fill="black" if r.get("categoria_mantida") else "red")
    img.save(pasta / "folha.jpg", quality=85)


def main() -> None:
    rodada = sys.argv[1]
    filtro = set(sys.argv[2:])
    todos = json.loads((BASE / "casos.json").read_text(encoding="utf-8"))
    casos = [c for c in todos if c["id"] in filtro] if filtro else todos
    pasta = BASE / "resultados" / rodada
    pasta.mkdir(parents=True, exist_ok=True)
    anteriores = {}
    if filtro and (pasta / "resultado.json").exists():
        anteriores = {
            r["id"]: r
            for r in json.loads((pasta / "resultado.json").read_text(encoding="utf-8"))["resultados"]
        }

    sessao_jev = requests.Session()
    sessao_jev.headers.update(
        {"Authorization": f"Bearer {teste_jev.chave()}", "TypeSafe-Danger-Zone-Images": "true"}
    )
    # A Runware reserva crédito por chamada em andamento; com saldo baixo, 6 em paralelo estouram.
    with ThreadPoolExecutor(3) as pool:
        novos = {r["id"]: r for r in pool.map(lambda c: rodar_caso(rodada, c, pasta, sessao_jev), casos)}
    por_id = {**anteriores, **novos}
    resultados = [por_id[c["id"]] for c in todos if c["id"] in por_id]

    custos = [r["custo_usd"] for r in resultados if r.get("custo_usd")]
    resumo = {
        "rodada": rodada,
        "casos": len(resultados),
        "geradas": sum("modelo" in r for r in resultados),
        "no_reserva": sum(r.get("modelo") == MODELOS[1] for r in resultados),
        "categoria_mantida": sum(bool(r.get("categoria_mantida")) for r in resultados),
        "custo_total_usd": round(sum(custos), 4),
    }
    (pasta / "resultado.json").write_text(
        json.dumps({"resumo": resumo, "resultados": resultados}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    folha(pasta, todos, resultados)
    print(json.dumps(resumo, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
