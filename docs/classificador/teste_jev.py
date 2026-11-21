"""Teste do Jev (TypeSafe) como classificador de fotos e versões da EuMini.

Uso, a partir da raiz do repositório:
    apps/backend/.venv/Scripts/python.exe -I docs/classificador/teste_jev.py [modelo] [repetições]

Lê a chave JEV_API_KEY de apps/backend/.env e grava o resultado em
docs/classificador/resultados/<modelo>.json. As perguntas vêm de
apps/backend/integrations/adapters/typesafe_questions.py, as mesmas de produção.
"""

import base64
import io
import json
import statistics
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

import requests
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
URL = "https://api.typesafe.ai/v1/systemone"
PRECO_ENTRADA_POR_MILHAO = 0.042  # US$, tokens de entrada (inclui as imagens)
VENDIDAS = {"person", "pet", "couple", "person_pet"}

# As perguntas e a decisão são as de produção: o teste mede exatamente o que roda no app.
sys.path.insert(0, str(RAIZ / "apps/backend/integrations/adapters"))
import typesafe_questions as Q  # noqa: E402

LADO_MINIMO = Q.MIN_SIDE


def perguntas(tipo: str) -> dict:
    return Q.questions("photo" if tipo == "foto" else "version")


def decidir(respostas: dict) -> str:
    return Q.decide(respostas)


def imagem_base64(arquivo: Path) -> str:
    im = Image.open(arquivo)
    if min(im.size) < LADO_MINIMO:
        escala = LADO_MINIMO / min(im.size)
        im = im.convert("RGB").resize((round(im.width * escala), round(im.height * escala)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90)
        return base64.b64encode(buf.getvalue()).decode()
    return base64.b64encode(arquivo.read_bytes()).decode()


def chave() -> str:
    for linha in (RAIZ / "apps/backend/.env").read_text(encoding="utf-8").splitlines():
        if linha.startswith("JEV_API_KEY="):
            return linha.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("JEV_API_KEY não está em apps/backend/.env")


def chamar(sessao: requests.Session, modelo: str, caso: dict) -> dict:
    ref = str(uuid.uuid4())
    corpo = {
        "model": modelo,
        "state": {"photo": ref},
        "assets": {
            ref: {
                "type": "image",
                "format": "jpg",
                "data_base64": imagem_base64(BASE / caso["arquivo"]),
            }
        },
        "questions": perguntas(caso["tipo"]),
    }
    for tentativa in range(4):
        t0 = time.monotonic()
        r = sessao.post(URL, json=corpo, timeout=60)
        dt = time.monotonic() - t0
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** tentativa * 2)
            continue
        break
    if r.status_code != 200:
        return {"erro": r.status_code, "corpo": r.text[:500], "segundos": round(dt, 3)}
    j = r.json()
    return {
        "segundos": round(dt, 3),
        "modelo": j.get("model"),
        "respostas": j["answers"],
        "tokens": j.get("usage", {}),
        "decisao": decidir(j["answers"]),
    }


def main() -> None:
    modelo = sys.argv[1] if len(sys.argv) > 1 else "jev-1.14.0"
    repeticoes = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    casos = json.loads((BASE / "casos.json").read_text(encoding="utf-8"))
    sessao = requests.Session()
    sessao.headers.update({"Authorization": f"Bearer {chave()}", "TypeSafe-Danger-Zone-Images": "true"})

    resultados = []
    for caso in casos:
        rodadas = [chamar(sessao, modelo, caso) for _ in range(repeticoes)]
        decisoes = [r.get("decisao", f"erro {r.get('erro')}") for r in rodadas]
        maioria = Counter(decisoes).most_common(1)[0][0]
        certo = maioria in caso["esperado"]
        resultados.append({**caso, "decisoes": decisoes, "maioria": maioria, "certo": certo, "rodadas": rodadas})
        marca = "ok " if certo else "ERR"
        estavel = "" if len(set(decisoes)) == 1 else f"  (instável: {decisoes})"
        print(f"{marca} {caso['id']:<28} esperado {'/'.join(caso['esperado']):<34} veio {maioria}{estavel}")

    validas = [r for res in resultados for r in res["rodadas"] if "decisao" in r]
    tempos = sorted(r["segundos"] for r in validas)
    entrada = [r["tokens"].get("input_tokens", 0) for r in validas]
    por_tipo = {}
    for tipo in ("foto", "versao"):
        grupo = [r for r in resultados if r["tipo"] == tipo]
        por_tipo[tipo] = {
            "casos": len(grupo),
            "certos": sum(r["certo"] for r in grupo),
            "venda_certa": sum((r["maioria"] in VENDIDAS) == (r["esperado"][0] in VENDIDAS) for r in grupo),
            "instaveis": sum(len(set(r["decisoes"])) > 1 for r in grupo),
        }
    resumo = {
        "modelo": modelo,
        "repeticoes": repeticoes,
        "chamadas": len(validas),
        "erros": sum(len(r["rodadas"]) for r in resultados) - len(validas),
        "por_tipo": por_tipo,
        "segundos_p50": statistics.median(tempos) if tempos else None,
        "segundos_p95": tempos[int(len(tempos) * 0.95) - 1] if tempos else None,
        "tokens_entrada_medio": round(statistics.mean(entrada)) if entrada else None,
        "custo_medio_usd": round(statistics.mean(entrada) * PRECO_ENTRADA_POR_MILHAO / 1e6, 6) if entrada else None,
    }
    (BASE / "resultados").mkdir(exist_ok=True)
    (BASE / "resultados" / f"{modelo}.json").write_text(
        json.dumps({"resumo": resumo, "resultados": resultados}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(resumo, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
