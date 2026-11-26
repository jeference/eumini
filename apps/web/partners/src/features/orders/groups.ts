import type { StatusTone } from "@eumini/design-tokens";

import type { OrderGroup } from "./hooks";

type GroupInfo = {
  label: string;
  tone: StatusTone;
  /** O que o parceiro faz agora, no detalhe do pedido. */
  nextStep: string;
};

/** `Record` exaustivo: um grupo novo sem rótulo é erro de compilação. */
export const GROUPS: Record<OrderGroup, GroupInfo> = {
  to_print: {
    label: "Para imprimir",
    tone: "neutral",
    nextStep: "Baixe os arquivos e toque em Iniciar produção quando começar a imprimir.",
  },
  in_production: {
    label: "Em produção",
    tone: "progress",
    nextStep: "Quando as peças estiverem prontas, envie uma foto e marque como prontas.",
  },
  awaiting_label: {
    label: "Aguardando etiqueta",
    tone: "progress",
    nextStep: "A EuMini está preparando a etiqueta. Você recebe um e-mail quando ela chegar.",
  },
  to_post: {
    label: "Para postar",
    tone: "progress",
    nextStep: "Baixe a etiqueta, cole na embalagem, poste e marque como postado.",
  },
  posted: {
    label: "Postado",
    tone: "success",
    nextStep: "Pedido postado. O ganho já está no seu extrato.",
  },
  cancelled: {
    label: "Cancelado",
    tone: "danger",
    nextStep: "Este pedido foi cancelado. Não imprima nem poste.",
  },
};

/** Ordem das abas: o que pede ação primeiro. */
export const TAB_ORDER: OrderGroup[] = [
  "to_print",
  "in_production",
  "awaiting_label",
  "to_post",
  "posted",
  "cancelled",
];

export function isOrderGroup(value: string | null): value is OrderGroup {
  return value !== null && (TAB_ORDER as string[]).includes(value);
}

/** Texto do prazo: atrasado, perto de vencer ou a data. */
export function deadlineTone(order: { is_overdue: boolean; is_due_soon: boolean }): StatusTone {
  if (order.is_overdue) return "danger";
  if (order.is_due_soon) return "progress";
  return "neutral";
}
