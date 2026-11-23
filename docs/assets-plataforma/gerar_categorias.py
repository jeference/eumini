"""Gera as imagens das categorias da home (Pessoa, Pet, Casal, Pessoa + Pet).

Uso, a partir da raiz:
    apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_categorias.py gerar
    apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_categorias.py \
        finalizar person-2 pet-1 couple-3 person_pet-1

`gerar` faz, para cada variação, uma foto sintética por texto na Runware (pessoas e pets
fictícios, sem direito de imagem de ninguém) e passa essa foto pelo prompt de produção
(`apps/backend/catalog/prompts.py`), como o worker faz. Grava tudo em `categorias/geracao/`,
com `folha.jpg` e `resultado.json`.

`finalizar` recorta a margem branca da miniatura escolhida em cada categoria, reduz e grava
`categorias/<categoria>-v<versao>.webp`, que vai para o bucket público
(`provision_s3.py --upload-assets`).
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
from PIL import Image, ImageChops, ImageDraw

RAIZ = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "apps/backend"))

from catalog import prompts as P  # noqa: E402  (módulo sem Django)

RUNWARE_URL = "https://api.runware.ai/v1"
TAMANHO = 1024
LADO_FINAL = 256  # cerca de 3x os 80 px exibidos na home
VERSAO = 1
SAIDA = BASE / "categorias"
GERACAO = SAIDA / "geracao"

_FOTO = (
    "Candid smartphone photo, natural daylight, realistic, sharp focus, full body visible "
    "from head to feet, simple everyday setting. "
)
# Três variações por categoria, com pessoas e pets diferentes, para escolher a melhor.
FOTOS: dict[str, list[str]] = {
    "person": [
        "A smiling Brazilian woman in her thirties with curly dark hair, wearing a yellow "
        "t-shirt and jeans, standing in a park.",
        "A cheerful Brazilian man in his twenties with short black hair and a light beard, "
        "wearing a blue hoodie and sneakers, standing on a sidewalk.",
        "A happy grandmother with short gray hair and glasses, wearing a floral dress and a "
        "cardigan, standing in a garden.",
    ],
    "pet": [
        "A caramel-colored Brazilian mixed-breed dog sitting on the grass, looking at the camera.",
        "An orange tabby cat sitting on a wooden floor, looking at the camera.",
        "A small black-and-white mixed-breed dog with a red collar sitting on a living room rug.",
    ],
    "couple": [
        "A young Brazilian couple hugging side by side and smiling, standing in a park.",
        "A middle-aged couple standing arm in arm and laughing on a beach boardwalk.",
        "Two young women, a couple, standing side by side holding hands and smiling on a "
        "city street.",
    ],
    "person_pet": [
        "A smiling Brazilian man in his thirties crouching next to his caramel mixed-breed dog "
        "in a park, his arm around the dog.",
        "A young woman with long brown hair sitting on a bench holding her gray cat in her lap.",
        "A teenage boy standing in a backyard holding a small white fluffy dog in his arms.",
    ],
}


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


def chamar(prompt: str, modelo: str, referencia: bytes | None) -> tuple[bytes, float | None]:
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
    }
    if referencia is not None:
        tarefa["inputs"] = {
            "referenceImages": ["data:image/png;base64," + base64.b64encode(referencia).decode()]
        }
    r = requests.post(
        RUNWARE_URL,
        json=[tarefa],
        headers={"Authorization": f"Bearer {ENV['RUNWARE_API_KEY']}"},
        timeout=180,
    )
    corpo = r.json()
    if corpo.get("errors") or corpo.get("error") or r.status_code >= 400:
        erro = corpo.get("errors") or corpo.get("error") or r.status_code
        raise RuntimeError(json.dumps(erro)[:300])
    item = next(d for d in corpo["data"] if d.get("imageDataURI"))
    return base64.b64decode(item["imageDataURI"].partition(",")[2]), item.get("cost")


def gerar_com_reserva(prompt: str, referencia: bytes | None) -> tuple[bytes, str, float | None]:
    """Modelo principal e, se falhar, o reserva, como o worker."""
    erros = []
    for modelo in MODELOS:
        for espera in (0, 15, 30, 60):
            time.sleep(espera)
            try:
                imagem, custo = chamar(prompt, modelo, referencia)
                return imagem, modelo, custo
            except Exception as exc:  # noqa: BLE001
                erro = str(exc)
                # Saldo reservado por chamadas em andamento: esperar não é falha do modelo.
                if "concurrentRequestLimitExceeded" not in erro:
                    break
        erros.append(f"{modelo}: {erro}")
    raise RuntimeError(" | ".join(erros))


def para_png(imagem: bytes) -> bytes:
    """Normaliza como o backend: RGB, até 1024 px, PNG."""
    im = Image.open(io.BytesIO(imagem)).convert("RGB")
    im.thumbnail((TAMANHO, TAMANHO))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def rodar_variacao(categoria: str, indice: int, descricao: str) -> dict:
    vid = f"{categoria}-{indice}"
    resultado = {"id": vid, "categoria": categoria, "prompt_foto": _FOTO + descricao}
    try:
        foto, modelo_foto, custo_foto = gerar_com_reserva(_FOTO + descricao, None)
        (GERACAO / f"{vid}-foto.png").write_bytes(foto)
        prompt = P.photo_prompt(category=categoria)
        mini, modelo, custo = gerar_com_reserva(prompt, para_png(foto))
        (GERACAO / f"{vid}.png").write_bytes(mini)
        resultado.update(
            modelo_foto=modelo_foto,
            modelo=modelo,
            prompt=prompt,
            custo_usd=round((custo_foto or 0) + (custo or 0), 4),
        )
        print(f"ok  {vid:<14} foto={modelo_foto} mini={modelo}")
    except Exception as exc:  # noqa: BLE001
        resultado["erro"] = str(exc)
        print(f"ERR {vid:<14} {exc}")
    return resultado


def folha(resultados: list[dict]) -> None:
    lado, cols = 300, 3
    linhas = len(FOTOS)
    img = Image.new("RGB", (cols * lado * 2, linhas * (lado + 28)), "white")
    d = ImageDraw.Draw(img)
    for linha, categoria in enumerate(FOTOS):
        for col in range(cols):
            vid = f"{categoria}-{col + 1}"
            x, y = col * lado * 2, linha * (lado + 28)
            for j, arquivo in enumerate((GERACAO / f"{vid}-foto.png", GERACAO / f"{vid}.png")):
                if arquivo.exists():
                    im = Image.open(arquivo).convert("RGB")
                    im.thumbnail((lado - 6, lado - 6))
                    img.paste(im, (x + j * lado + (lado - im.width) // 2, y + 26))
            d.text((x + 6, y + 6), vid, fill="black")
    img.save(GERACAO / "folha.jpg", quality=85)


def gerar() -> None:
    GERACAO.mkdir(parents=True, exist_ok=True)
    tarefas = [
        (categoria, i + 1, descricao)
        for categoria, descricoes in FOTOS.items()
        for i, descricao in enumerate(descricoes)
    ]
    # A Runware reserva crédito por chamada em andamento; poucas em paralelo.
    with ThreadPoolExecutor(3) as pool:
        resultados = list(pool.map(lambda t: rodar_variacao(*t), tarefas))
    resumo = {
        "data": time.strftime("%Y-%m-%d"),
        "prompt_version": P.PROMPT_VERSION,
        "geradas": sum("modelo" in r for r in resultados),
        "custo_total_usd": round(sum(r.get("custo_usd") or 0 for r in resultados), 4),
    }
    (GERACAO / "resultado.json").write_text(
        json.dumps({"resumo": resumo, "resultados": resultados}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    folha(resultados)
    print(json.dumps(resumo, ensure_ascii=False, indent=1))


def recortar(im: Image.Image) -> Image.Image:
    """Tira a margem branca em volta da figura e devolve um quadrado com folga pequena."""
    im = im.convert("RGB")
    fundo = Image.new("RGB", im.size, "white")
    # Tolerância para o branco levemente sujo e para a sombra de contato bem clara.
    diff = ImageChops.difference(im, fundo).convert("L").point(lambda v: 255 if v > 18 else 0)
    caixa = diff.getbbox() or (0, 0, im.width, im.height)
    largura, altura = caixa[2] - caixa[0], caixa[3] - caixa[1]
    lado = int(max(largura, altura) * 1.08)
    quadrado = Image.new("RGB", (lado, lado), "white")
    quadrado.paste(im.crop(caixa), ((lado - largura) // 2, (lado - altura) // 2))
    return quadrado


def finalizar(escolhas: list[str]) -> None:
    for vid in escolhas:
        categoria = vid.rsplit("-", 1)[0]
        if categoria not in FOTOS:
            raise SystemExit(f"categoria desconhecida em {vid}")
        im = recortar(Image.open(GERACAO / f"{vid}.png"))
        im = im.resize((LADO_FINAL, LADO_FINAL), Image.LANCZOS)
        destino = SAIDA / f"{categoria}-v{VERSAO}.webp"
        im.save(destino, "WEBP", quality=88, method=6)
        print(f"{vid} -> {destino.relative_to(RAIZ)} ({destino.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("gerar", "finalizar"):
        raise SystemExit(__doc__)
    if sys.argv[1] == "gerar":
        gerar()
    else:
        finalizar(sys.argv[2:])
