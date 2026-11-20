from common.fsm import FSM, Transition
from creations.models import Creation, ProviderTask

S = Creation.Status
CREATION_FSM = FSM(
    [
        Transition(S.CLASSIFYING, S.GENERATING_IMAGE, "photo_accepted"),
        Transition(S.CLASSIFYING, S.REJECTED, "photo_rejected"),
        Transition(S.CLASSIFYING, S.FAILED, "classification_failed"),
        # Foto aceita, mas a geração não pôde começar (cota do dia ou teto de gasto).
        Transition(S.CLASSIFYING, S.FAILED, "image_failed"),
        Transition(S.GENERATING_IMAGE, S.READY, "image_ready"),
        Transition(S.GENERATING_IMAGE, S.FAILED, "image_failed"),
        # Tentar de novo volta à etapa que falhou: a leitura da foto ou a imagem.
        Transition(S.FAILED, S.CLASSIFYING, "retry_classification"),
        Transition(S.FAILED, S.GENERATING_IMAGE, "retry"),
    ]
)

T = ProviderTask.Status
TASK_ACTIVE = (T.QUEUED, T.RUNNING)
