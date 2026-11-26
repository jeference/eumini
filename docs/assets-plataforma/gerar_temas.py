"""Gera as miniaturas dos temas do envio da foto (Natal, GTA VI).

Uso, a partir da raiz:
    apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_temas.py gerar
    apps/backend/.venv/Scripts/python.exe -I docs/assets-plataforma/gerar_temas.py \
        finalizar christmas-pet-1 gta6-person-2

`gerar` passa fotos sintéticas das categorias (`categorias/geracao/<variação>-foto.png`, pessoas
e pets fictícios) pelo prompt de produção com o tema (`apps/backend/catalog/prompts.py`), como o
worker faz. Grava em `temas/geracao/`, com `folha.jpg` e `resultado.json`.

`finalizar` recorta a margem branca da miniatura escolhida em cada tema, reduz e grava
`temas/<tema>-v<versao>.webp`, que vai para o bucket público (`provision_s3.py --upload-assets`).
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import gerar_categorias as G  # noqa: E402  (Runware, normalização e recorte)
from gerar_categorias import P  # noqa: E402

VERSAO = 1
SAIDA = BASE / "temas"
GERACAO = SAIDA / "geracao"
# Tema -> variações de `categorias/geracao` usadas como foto de entrada.
VARIACOES = {
    "christmas": ["pet-1", "couple-1"],
    "gta6": ["person-1", "person-2"],
}


def rodar(tema: str, variacao: str) -> dict:
    vid = f"{tema}-{variacao}"
    categoria = variacao.rsplit("-", 1)[0]
    prompt = P.photo_prompt(category=categoria, theme=tema)
    resultado = {"id": vid, "tema": tema, "categoria": categoria, "prompt": prompt}
    try:
        foto = (G.GERACAO / f"{variacao}-foto.png").read_bytes()
        mini, modelo, custo = G.gerar_com_reserva(prompt, G.para_png(foto))
        (GERACAO / f"{vid}.png").write_bytes(mini)
        resultado.update(modelo=modelo, custo_usd=custo)
        print(f"ok  {vid:<22} {modelo}")
    except Exception as exc:  # noqa: BLE001
        resultado["erro"] = str(exc)
        print(f"ERR {vid:<22} {exc}")
    return resultado


def folha(resultados: list[dict]) -> None:
    lado = 300
    img = Image.new("RGB", (len(resultados) * lado, lado + 28), "white")
    d = ImageDraw.Draw(img)
    for i, r in enumerate(resultados):
        arquivo = GERACAO / f"{r['id']}.png"
        if arquivo.exists():
            im = Image.open(arquivo).convert("RGB")
            im.thumbnail((lado - 6, lado - 6))
            img.paste(im, (i * lado + (lado - im.width) // 2, 26))
        d.text((i * lado + 6, 6), r["id"], fill="black")
    img.save(GERACAO / "folha.jpg", quality=85)


def gerar() -> None:
    GERACAO.mkdir(parents=True, exist_ok=True)
    tarefas = [(tema, v) for tema, variacoes in VARIACOES.items() for v in variacoes]
    with ThreadPoolExecutor(3) as pool:
        resultados = list(pool.map(lambda t: rodar(*t), tarefas))
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


def finalizar(escolhas: list[str]) -> None:
    for vid in escolhas:
        tema = vid.split("-", 1)[0]
        if tema not in VARIACOES:
            raise SystemExit(f"tema desconhecido em {vid}")
        im = G.recortar(Image.open(GERACAO / f"{vid}.png"))
        im = im.resize((G.LADO_FINAL, G.LADO_FINAL), Image.LANCZOS)
        destino = SAIDA / f"{tema}-v{VERSAO}.webp"
        im.save(destino, "WEBP", quality=88, method=6)
        print(f"{vid} -> {destino.relative_to(G.RAIZ)} ({destino.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("gerar", "finalizar"):
        raise SystemExit(__doc__)
    if sys.argv[1] == "gerar":
        gerar()
    else:
        finalizar(sys.argv[2:])
