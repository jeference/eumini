"use client";

import { Button } from "@kubo/ui/button";
import { Callout } from "@kubo/ui/callout";
import { Card } from "@kubo/ui/card";
import { EmptyState } from "@kubo/ui/empty-state";
import { formatDate } from "@kubo/ui/lib/format";
import { ORDER_STATUS } from "@kubo/ui/lib/status";
import { Skeleton } from "@kubo/ui/skeleton";
import { StatusBadge } from "@kubo/ui/status-badge";
import type { Schemas } from "@kubo/api-client";
import Link from "next/link";

import { OrderPayment } from "@/features/orders/components/order-payment";
import { OrderSummary } from "@/features/orders/components/order-summary";
import { OrderTimeline } from "@/features/orders/components/order-timeline";
import { useOrder } from "@/features/orders/hooks";

/** "Pix" ou "Cartão Visa •••• 4242". */
function paymentLabel(charge: Schemas["Charge"]): string {
  if (charge.method !== "CARD") return "Pix";
  const brand = charge.card_brand
    ? ` ${charge.card_brand.charAt(0)}${charge.card_brand.slice(1).toLowerCase()}`
    : "";
  const lastFour = charge.card_last_four ? ` •••• ${charge.card_last_four}` : "";
  return `Cartão${brand}${lastFour}`;
}

/** Hub do pedido: o status decide o que aparece, inclusive o pagamento. */
export function OrderDetail({ id }: { id: string }) {
  const { data: order, isLoading, isError } = useOrder(id);

  if (isError) {
    return (
      <div className="mx-auto max-w-xl py-8">
        <EmptyState
          title="Pedido não encontrado"
          description="Use o link enviado ao seu e-mail, ou entre na sua conta."
          action={
            <Button asChild variant="primary">
              <Link href="/acompanhar">Acompanhar pedido</Link>
            </Button>
          }
        />
      </div>
    );
  }
  if (isLoading || !order) {
    return (
      <div className="mx-auto max-w-3xl space-y-3">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const badge = ORDER_STATUS[order.status];
  const isPaidOrLater = !["pending_payment", "expired"].includes(order.status);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Esperando o pagamento, a tela é só ele: número, status e data vêm depois. */}
      {order.status === "pending_payment" ? (
        <h1 className="sr-only">Pagamento do pedido</h1>
      ) : (
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="font-display text-3xl font-semibold tracking-tight">
              Pedido {order.number}
            </h1>
            <StatusBadge label={badge.label} tone={badge.tone} />
          </div>
          <p className="mt-1 text-sm text-muted">Feito em {formatDate(order.created_at)}</p>
        </div>
      )}

      {order.status === "paid" && (
        <Callout tone="accent" role="status" className="p-4 text-base">
          <strong>Recebemos seu pagamento!</strong> Enviamos o link de acompanhamento para{" "}
          {order.customer_email}.
        </Callout>
      )}

      <OrderPayment order={order} />

      {order.status === "refunded" && (
        <Callout role="status" className="p-4 text-base text-ink">
          Este pedido foi reembolsado. O valor volta para a forma de pagamento usada.
        </Callout>
      )}

      {isPaidOrLater && <OrderTimeline status={order.status} />}

      <OrderSummary
        items={order.items}
        subtotalCents={order.subtotal_cents}
        shippingCents={order.shipping_cents}
        totalCents={order.total_cents}
        shippingLabel={order.shipping_service_name}
        deliveryDays={order.delivery_days}
        shipment={order.shipment}
      />

      <Card className="p-5 text-sm">
        <h2 className="font-display text-lg font-semibold">Entrega</h2>
        <p className="mt-2">{order.customer_name}</p>
        <p className="text-muted">
          {order.street}, {order.address_number}
          {order.complement ? `, ${order.complement}` : ""}
          <br />
          {order.neighborhood}, {order.city}/{order.state}
          <br />
          CEP {order.postal_code.slice(0, 5)}-{order.postal_code.slice(5)}
        </p>
        <p className="mt-2 text-muted">CPF {order.cpf_masked}</p>
        {isPaidOrLater && order.charge && (
          <p className="mt-2 text-muted">Pago com {paymentLabel(order.charge)}</p>
        )}
      </Card>
    </div>
  );
}
