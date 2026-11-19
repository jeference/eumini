"""Teste dos prompts por categoria no estilo único (o antigo "pixar").

Uso, a partir da raiz do repositório:
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

# --- Camadas do prompt -------------------------------------------------------------------

ESTILO = (
    "Turn the main subject of this reference image into a 3D model from a modern animated "
    f"family movie: {P._PIXAR_LOOK} Keep it recognizably the same: same faces, features, hair, "
    "clothing and distinctive details, and do not add anyone or anything that is not in the "
    "reference."
)

IMPRESSAO = (
    "It will be 3D printed as a small figurine, so it must be sturdy: chunky simplified forms, "
    "thick arms and legs, simple hands with the fingers together, kept close to the body or "
    "touching it, nothing thin sticking out, and ears, tails and accessories attached to the body."
)

PROPORCAO = (
    "stylized proportions about four heads tall, a head only slightly larger than realistic and "
    "large expressive eyes"
)
ANIMAL = (
    "keeps its natural body and anatomy, slightly stylized, with a friendly cartoon face and big "
    "expressive eyes"
)

CATEGORIA = {
    "person": (
        f"The subject is one person. Give them {PROPORCAO}, and show them full body, standing on "
        "both feet with the arms relaxed at the sides, even if the photo shows only part of them."
    ),
    "pet": (
        f"The subject is one animal. It {ANIMAL}, shown whole in a calm, compact natural pose, "
        "sitting or standing, even if the photo shows only part of it."
    ),
    "couple": (
        "The subject is two people, made as one single figurine. Both are shown full body, standing "
        "side by side and touching, with an arm around each other or holding hands, so that the "
        f"two figures are joined into one piece. Give both {PROPORCAO}. The two figures share the "
        "same few colors."
    ),
    "person_pet": (
        "The subject is one person with one animal, made as one single figurine. The person is "
        f"shown full body, standing, with {PROPORCAO}, holding the animal in their arms or with "
        "the animal sitting at their feet pressed against their legs, so that they are joined into "
        "one piece. If the animal is too large to hold, it stands right beside the person, touching "
        f"them, scaled down to fit. The animal {ANIMAL}. Person and animal share the same few colors."
    ),
}

SEM_BASE = "isolated on a plain white background with a soft contact shadow and no base or pedestal."
COM_BASE = (
    "standing on a small plain round base in one of the figure's colors, isolated on a plain "
    "white background with a soft contact shadow."
)


BASE_ESCURA = (
    "standing on a small plain round base in the figure's dark color, isolated on a plain white "
    "background with a soft contact shadow."
)

_CORES_INICIO = (
    "\n\nColor plan, more important than color accuracy: the finished figurine, base included, "
    f"uses exactly {P.MAX_PRINT_COLORS} colors from the list, no more, and each part is one flat "
    "color with no prints, patterns, stripes or logos. These rules change only the colors, never "
    "what the subject is: every shape and feature above stays. "
)
_CORES_FIM = " Do not add any person, animal or object that is not in the reference."
_PELE = "skin (light skin, or brown for dark skin)"
CORES = {
    "person": (
        f"Use {_PELE}; one dark color (black or brown) shared by the hair, beard, eyebrows, eyes, "
        "shoes and base; one color for the top; and one color for the trousers or skirt. A dress "
        "or one-piece outfit is a single color."
    ),
    "pet": (
        "Use the animal's main color; a second color for its largest marking, or for the belly, "
        "muzzle or chest; black shared by the eyes, nose and base; and one color for a collar or "
        "accessory, if it has one. Beak, paws, claws, mouth and tongue reuse one of these colors."
    ),
    "couple": (
        f"The two people share the same {P.MAX_PRINT_COLORS} colors: {_PELE}; one dark color "
        "(black or brown) shared by both people's hair, eyes, shoes and the base; one color for "
        "one person's clothes; and one color for the other person's clothes. Trousers, ties and "
        "flowers reuse one of these colors. If their skin tones differ, light skin and brown both "
        "count, so the two outfits share one color."
    ),
    "person_pet": (
        f"The person and the animal share the same {P.MAX_PRINT_COLORS} colors: {_PELE}; one dark "
        "color (black or brown) shared by the person's hair, eyes and shoes, the animal's eyes and "
        "nose, and the base; one color for all of the person's clothes; and one color for the "
        "animal's fur, feathers or coat. The animal's markings, mouth and tongue, and any "
        "accessory, reuse one of these colors."
    ),
}


def prompt_camadas(categoria: str, base: str, cores: str | None = None) -> str:
    plano = P._COLOR_PLAN if cores is None else _CORES_INICIO + cores + _CORES_FIM
    return (
        f"{P._COLOR_RULE}{ESTILO} {CATEGORIA[categoria]} {IMPRESSAO} {P._STYLE_IGNORE} "
        f"Whole subject alone, {P._STYLE_FRAME} {base}{plano}"
    )


RODADAS = {
    # Linha de base: o prompt Pixar que está no código hoje, igual para todas as categorias.
    "r0": lambda categoria: P.GENERATION["STYLES"]["pixar"]["STANDARDIZE_PROMPT_TEMPLATE"],
    # Bloco por categoria e regras de impressão, sem base.
    "r1": lambda categoria: prompt_camadas(categoria, SEM_BASE),
    # Igual à r1, com base redonda.
    "r2": lambda categoria: prompt_camadas(categoria, COM_BASE),
    # Plano de cores por categoria, com base na cor escura da figura.
    "r3": lambda categoria: prompt_camadas(categoria, BASE_ESCURA, CORES[categoria]),
}

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
    prompt = RODADAS[rodada](caso["categoria"])
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
