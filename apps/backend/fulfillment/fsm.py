from common.fsm import FSM, Transition
from fulfillment.models import ProductionJob

S = ProductionJob.Status
JOB_FSM = FSM(
    [
        Transition(S.UNASSIGNED, S.ASSIGNED, "assign"),
        Transition(S.ASSIGNED, S.UNASSIGNED, "refuse"),
        Transition(S.ASSIGNED, S.IN_PRODUCTION, "start"),
        Transition(S.IN_PRODUCTION, S.READY_TO_SHIP, "mark_ready"),
        Transition(S.READY_TO_SHIP, S.SHIPPED, "post"),
        # A equipe retira o pedido do parceiro enquanto ele não foi postado.
        *(
            Transition(source, S.UNASSIGNED, "unassign")
            for source in (S.ASSIGNED, S.IN_PRODUCTION, S.READY_TO_SHIP)
        ),
        *(
            Transition(source, S.CANCELLED, "cancel")
            for source in (S.UNASSIGNED, S.ASSIGNED, S.IN_PRODUCTION, S.READY_TO_SHIP)
        ),
    ]
)
