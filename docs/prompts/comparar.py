"""Folha de comparação: uma linha por caso, com a foto e a imagem de cada rodada.

Uso: apps/backend/.venv/Scripts/python.exe -I docs/prompts/comparar.py <saida.jpg> r0 r1 r2 [--ids a,b]
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
LADO = 340


def main() -> None:
    args = sys.argv[1:]
    ids = None
    if "--ids" in args:
        i = args.index("--ids")
        ids = set(args[i + 1].split(","))
        args = args[:i] + args[i + 2 :]
    saida, rodadas = Path(args[0]), args[1:]
    casos = json.loads((BASE / "casos.json").read_text(encoding="utf-8"))
    if ids:
        casos = [c for c in casos if c["id"] in ids]
    jev = {
        r: {x["id"]: x.get("jev") for x in json.loads((BASE / "resultados" / r / "resultado.json").read_text(encoding="utf-8"))["resultados"]}
        for r in rodadas
    }
    img = Image.new("RGB", ((len(rodadas) + 1) * LADO, len(casos) * (LADO + 24) + 24), "white")
    d = ImageDraw.Draw(img)
    for j, titulo in enumerate(["foto", *rodadas]):
        d.text((j * LADO + 8, 6), titulo, fill="black")
    for i, caso in enumerate(casos):
        y = 24 + i * (LADO + 24)
        arquivos = [BASE / caso["arquivo"], *(BASE / "resultados" / r / f"{caso['id']}.jpg" for r in rodadas)]
        for j, arquivo in enumerate(arquivos):
            x = j * LADO
            if arquivo.exists():
                im = Image.open(arquivo).convert("RGB")
                im.thumbnail((LADO - 8, LADO - 8))
                img.paste(im, (x + (LADO - im.width) // 2, y + 22))
            rotulo = caso["id"] if j == 0 else f"jev={jev[rodadas[j - 1]].get(caso['id'])}"
            certo = j == 0 or jev[rodadas[j - 1]].get(caso["id"]) == caso["categoria"]
            d.text((x + 8, y + 6), rotulo, fill="black" if certo else "red")
    img.save(saida, quality=85)


if __name__ == "__main__":
    main()
