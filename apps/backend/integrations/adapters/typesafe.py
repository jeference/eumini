"""TypeSafe (https://typesafe.ai): o classificador Jev. Uma chamada por imagem.

A entrada de imagem é experimental e precisa do cabeçalho `TypeSafe-Danger-Zone-Images` em
cada chamada. O teste que aprovou o modelo e as perguntas está em `docs/classificador/`.
"""

from __future__ import annotations

import base64
import uuid

import requests
import structlog
from django.conf import settings

from integrations.adapters import typesafe_questions as q
from integrations.ports import (
    ClassificationResult,
    ImageClassificationPort,
    ProviderPermanentError,
    ProviderTemporaryError,
)

_URL = "https://api.typesafe.ai/v1/systemone"
_TIMEOUT_SECONDS = 30
# US$ por milhão de tokens de entrada (a imagem entra como tokens de entrada).
_INPUT_PRICE_PER_MILLION = 0.042
log = structlog.get_logger(__name__)


class TypeSafeClassificationAdapter(ImageClassificationPort):
    provider = "typesafe"

    def classify(self, *, image: bytes, target: str) -> ClassificationResult:
        ref = str(uuid.uuid4())
        body = {
            "model": settings.JEV_MODEL,
            "state": {"photo": ref},
            "assets": {
                ref: {
                    "type": "image",
                    "format": "png",
                    "data_base64": base64.b64encode(image).decode("ascii"),
                }
            },
            "questions": q.questions(target),
        }
        headers = {
            "Authorization": f"Bearer {settings.JEV_API_KEY}",
            "TypeSafe-Danger-Zone-Images": "true",
        }
        try:
            response = requests.post(_URL, json=body, headers=headers, timeout=_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            log.warning("typesafe_request_failed", error=str(exc))
            raise ProviderTemporaryError("TypeSafe indisponível.") from exc
        if response.status_code == 429 or response.status_code >= 500:
            raise ProviderTemporaryError(f"TypeSafe respondeu {response.status_code}.")
        if response.status_code >= 400:
            log.warning("typesafe_error", status=response.status_code, body=response.text[:300])
            raise ProviderPermanentError(f"TypeSafe respondeu {response.status_code}.")
        try:
            data = response.json()
            answers = data["answers"]
            subject = answers["subject"]
            character = answers["character"]["noul"]
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderPermanentError("Resposta inesperada da TypeSafe.") from exc

        input_tokens = (data.get("usage") or {}).get("input_tokens")
        return ClassificationResult(
            result=q.decide(answers),
            confidence=subject.get("confidence"),
            probabilities=subject.get("probabilities") or {},
            character_probability=character,
            model=data.get("model") or settings.JEV_MODEL,
            question_set_version=q.QUESTION_SET_VERSION,
            cost_usd=(
                input_tokens * _INPUT_PRICE_PER_MILLION / 1_000_000 if input_tokens else None
            ),
        )
