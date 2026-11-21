import type { StatusTone } from "@eumini/design-tokens";

export type OrderStatus =
  "pending_payment" | "paid" | "in_production" | "shipped" | "delivered" | "expired" | "refunded";

export type CreationStatus = "classifying" | "rejected" | "generating_image" | "ready" | "failed";

/** `Record` exaustivo: um status novo sem rótulo é erro de compilação. */
export const ORDER_STATUS: Record<OrderStatus, { label: string; tone: StatusTone }> = {
  pending_payment: { label: "Aguardando pagamento", tone: "neutral" },
  paid: { label: "Confirmado", tone: "progress" },
  in_production: { label: "Em produção", tone: "progress" },
  shipped: { label: "Enviado", tone: "progress" },
  delivered: { label: "Entregue", tone: "success" },
  expired: { label: "Expirado", tone: "danger" },
  refunded: { label: "Reembolsado", tone: "danger" },
};

export const CREATION_STATUS: Record<CreationStatus, { label: string; tone: StatusTone }> = {
  classifying: { label: "Lendo a foto", tone: "progress" },
  rejected: { label: "Foto não aceita", tone: "danger" },
  generating_image: { label: "Gerando imagem", tone: "progress" },
  ready: { label: "Pronta para comprar", tone: "success" },
  failed: { label: "Não deu certo", tone: "danger" },
};
