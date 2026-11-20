"use client";

import { Button } from "@kubo/ui/button";
import { Card } from "@kubo/ui/card";
import { EmptyState } from "@kubo/ui/empty-state";
import { RadioCard } from "@kubo/ui/radio-card";
import { Skeleton } from "@kubo/ui/skeleton";
import { CreditCard, type LucideIcon, QrCode } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { STEP_HEADING_ID } from "@/features/checkout/components/checkout-step";
import { OrderPayment } from "@/features/orders/components/order-payment";
import { OrderSummary } from "@/features/orders/components/order-summary";
import { useOrder, usePayOrder } from "@/features/orders/hooks";
import { messageOf } from "@/lib/errors";

function MethodLabel({ icon: Icon, title }: { icon: LucideIcon; title: string }) {
  return (
    <span className="flex items-center gap-2.5">
      <Icon aria-hidden className="size-5 text-accent" />
      <span className="text-sm font-semibold">{title}</span>
    </span>
  );
}

/**
 * Última etapa do checkout: o cliente escolhe a forma de pagamento (nada vem marcado;
 * cartão aparece como "Em breve") e, no Pix, gera o QR Code com o botão. Vem do pedido
 * (não do carrinho nem do formulário), para sobreviver a um recarregar. Pago, segue
 * para o pedido.
 */
export function PayStep({ orderId }: { orderId: string }) {
  const router = useRouter();
  const { data: order, isError } = useOrder(orderId);
  const pay = usePayOrder(orderId);
  const [method, setMethod] = useState<"pix" | null>(null);
  const settled = Boolean(order && !["pending_payment", "expired"].includes(order.status));
  const hasCharge = order?.status === "pending_payment" && order.charge?.status === "pending";
  const needsCharge = order?.status === "pending_payment" && !hasCharge;
  // Já tem PIX válido (recarregou depois de gerar): o Pix já foi escolhido.
  const pixChosen = method === "pix" || hasCharge;

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
              <RadioCard
                name="payment_method"
                size="sm"
                checked={pixChosen}
                onSelect={() => setMethod("pix")}
              >
                <MethodLabel icon={QrCode} title="Pix" />
              </RadioCard>
              {/* Ainda não aceito: aparece para o cliente saber que vem aí. */}
              <RadioCard
                name="payment_method"
                size="sm"
                checked={false}
                onSelect={() => undefined}
                disabled
                aside={<span className="text-xs font-semibold text-muted">Em breve</span>}
              >
                <MethodLabel icon={CreditCard} title="Cartão de crédito" />
              </RadioCard>
            </div>
            {pixChosen && needsCharge && (
              <div className="mt-4 flex justify-end">
                <Button
                  type="button"
                  variant="primary"
                  size="lg"
                  className="w-full sm:w-auto"
                  pending={pay.isPending}
                  onClick={() =>
                    pay.mutate(undefined, { onError: (error) => toast.error(messageOf(error)) })
                  }
                >
                  <QrCode aria-hidden />
                  Gerar QR Code
                </Button>
              </div>
            )}
          </fieldset>
        </Card>
        {(!order || settled) && <Skeleton className="h-72 w-full" />}
        {order && !settled && (pixChosen || order.status === "expired") && (
          <OrderPayment order={order} autoGenerate={false} />
        )}
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
