"use client";

import { Button } from "@kubo/ui/button";
import { Card } from "@kubo/ui/card";
import { EmptyState } from "@kubo/ui/empty-state";
import { RadioCard } from "@kubo/ui/radio-card";
import { Skeleton } from "@kubo/ui/skeleton";
import { CreditCard, type LucideIcon, QrCode } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { STEP_HEADING_ID } from "@/features/checkout/components/checkout-step";
import { OrderPayment } from "@/features/orders/components/order-payment";
import { OrderSummary } from "@/features/orders/components/order-summary";
import { useOrder } from "@/features/orders/hooks";

function MethodLabel({
  icon: Icon,
  title,
  detail,
}: {
  icon: LucideIcon;
  title: string;
  detail: string;
}) {
  return (
    <span className="flex items-center gap-2.5">
      <Icon aria-hidden className="size-5 text-accent" />
      <span>
        <span className="block text-sm font-semibold">{title}</span>
        <span className="block text-xs text-muted">{detail}</span>
      </span>
    </span>
  );
}

/**
 * Última etapa do checkout: escolha da forma de pagamento (só Pix por enquanto; cartão
 * aparece como "Em breve") e o PIX do pedido já criado, gerado aqui. Vem do pedido (não do carrinho
 * nem do formulário), para sobreviver a um recarregar. Pago, segue para o pedido.
 */
export function PayStep({ orderId }: { orderId: string }) {
  const router = useRouter();
  const { data: order, isError } = useOrder(orderId);
  const settled = Boolean(order && !["pending_payment", "expired"].includes(order.status));

  useEffect(() => {
    if (settled) router.replace(`/pedidos/${orderId}`);
  }, [settled, orderId, router]);

  if (isError) {
    return (
      <div className="mx-auto max-w-xl py-8">
        <EmptyState
          title="Pedido não encontrado"
          description="Volte ao carrinho para finalizar a compra de novo."
          action={
            <Button asChild variant="primary">
              <Link href="/carrinho">Voltar ao carrinho</Link>
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px] lg:gap-8">
      <section aria-labelledby={STEP_HEADING_ID} className="space-y-4">
        <Card asChild className="p-5 sm:p-6">
          <fieldset aria-labelledby={STEP_HEADING_ID}>
            <h2
              id={STEP_HEADING_ID}
              tabIndex={-1}
              className="font-display text-lg font-semibold outline-none"
            >
              Forma de pagamento
            </h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <RadioCard name="payment_method" checked onSelect={() => undefined}>
                <MethodLabel icon={QrCode} title="Pix" detail="Aprovação na hora" />
              </RadioCard>
              {/* Ainda não aceito: aparece para o cliente saber que vem aí. */}
              <RadioCard
                name="payment_method"
                checked={false}
                onSelect={() => undefined}
                disabled
                aside={<span className="text-xs font-semibold text-muted">Em breve</span>}
              >
                <MethodLabel icon={CreditCard} title="Cartão de crédito" detail="Indisponível" />
              </RadioCard>
            </div>
          </fieldset>
        </Card>
        {!order || settled ? <Skeleton className="h-72 w-full" /> : <OrderPayment order={order} />}
      </section>
      {order && (
        <div className="h-fit max-lg:hidden lg:sticky lg:top-6">
          <OrderSummary
            items={order.items}
            subtotalCents={order.subtotal_cents}
            shippingCents={order.shipping_cents}
            totalCents={order.total_cents}
            shippingLabel={order.shipping_service_name}
            deliveryDays={order.delivery_days}
            shipment={order.shipment}
          />
        </div>
      )}
    </div>
  );
}
