import type { Schemas } from "@eumini/api-client";
import type { StatusTone } from "@eumini/design-tokens";

export type Stage = Schemas["StageEnum"];
export type Queue = keyof Schemas["StaffQueueSummary"];

/** `Record` exaustivo: uma etapa nova sem rótulo é erro de compilação. */
export const STAGES: Record<Stage, { label: string; tone: StatusTone }> = {
  none: { label: "Sem produção", tone: "neutral" },
  unassigned: { label: "Sem parceiro", tone: "danger" },
  assigned: { label: "Com o parceiro", tone: "progress" },
  in_production: { label: "Imprimindo", tone: "progress" },
  awaiting_label: { label: "Falta etiqueta", tone: "danger" },
  to_post: { label: "Para postar", tone: "progress" },
  shipped: { label: "Postado", tone: "success" },
  cancelled: { label: "Cancelado", tone: "neutral" },
  mixed: { label: "Itens em etapas diferentes", tone: "danger" },
};

export const QUEUES: Record<Queue, { label: string; hint: string; empty: string }> = {
  to_assign: {
    label: "A atribuir",
    hint: "Pagos e sem parceiro",
    empty: "Todo pedido pago já tem parceiro.",
  },
  missing_file: {
    label: "Sem 3MF",
    hint: "Itens sem arquivo de impressão",
    empty: "Todos os itens em produção têm 3MF.",
  },
  awaiting_label: {
    label: "Aguardando etiqueta",
    hint: "Peças prontas, falta a etiqueta",
    empty: "Nenhuma peça esperando etiqueta.",
  },
  overdue: {
    label: "Atrasados",
    hint: "Prazo de postagem vencido",
    empty: "Nenhum pedido atrasado.",
  },
  issues: {
    label: "Com problema",
    hint: "Problemas reportados em aberto",
    empty: "Nenhum problema em aberto.",
  },
  to_deliver: {
    label: "A confirmar entrega",
    hint: "Postados, falta marcar entregue",
    empty: "Nenhum envio esperando confirmação.",
  },
};

/** Ordem na tela Hoje: o que trava a produção primeiro. */
export const QUEUE_ORDER: Queue[] = [
  "to_assign",
  "missing_file",
  "awaiting_label",
  "overdue",
  "issues",
  "to_deliver",
];

export const EVENT_LABELS: Record<string, string> = {
  created: "Pedido criado",
  pay: "Pagamento confirmado",
  pay_late: "Pagamento confirmado depois de expirar",
  expire: "PIX expirado",
  renew_payment: "Novo PIX gerado",
  refund: "Reembolsado",
  disputed: "Pagamento em disputa",
  start_production: "Pedido em produção",
  ship: "Pedido enviado",
  deliver: "Pedido entregue",
  assign: "Atribuído ao parceiro",
  unassign: "Retirado do parceiro",
  refuse: "Recusado pelo parceiro",
  start: "Parceiro iniciou a impressão",
  mark_ready: "Peças prontas",
  post: "Parceiro postou",
  cancel: "Produção cancelada",
  production_file_added: "3MF enviado",
  label_attached: "Etiqueta anexada",
  label_replaced: "Etiqueta substituída",
  issue_reported: "Problema reportado",
  issue_resolved: "Problema resolvido",
};

/** A cobrança tem eventos com o mesmo nome dos do pedido ("created", "pay"). */
const CHARGE_EVENT_LABELS: Record<string, string> = {
  created: "Cobrança criada",
  pay: "Cobrança paga",
  expire: "Cobrança expirada",
  fail: "Cobrança recusada",
  refund: "Cobrança reembolsada",
};

export function eventLabel(event: string, aggregate = "order"): string {
  if (aggregate === "charge") return CHARGE_EVENT_LABELS[event] ?? `Cobrança: ${event}`;
  return EVENT_LABELS[event] ?? event;
}
