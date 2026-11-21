"use client";

import { ApiError, type Schemas } from "@eumini/api-client";
import { Button } from "@eumini/ui/button";
import { Card } from "@eumini/ui/card";
import { Skeleton } from "@eumini/ui/skeleton";
import { Hourglass } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { toast } from "sonner";

import { PixPayment } from "@/features/orders/components/pix-payment";
import { usePayOrder } from "@/features/orders/hooks";
import { messageOf } from "@/lib/errors";

/**
 * Pagamento de um pedido aguardando pagamento:
 * - cartão em análise: só avisa (o polling do pedido mostra quando decidir);
 * - PIX válido: mostra o PIX;
 * - sem cobrança válida (ou cartão recusado): gera um PIX (uma tentativa automática);
 * - expirado: oferece um novo PIX.
 * Fora de `pending_payment` e `expired`, não mostra nada.
 */
export function OrderPayment({ order }: { order: Schemas["OrderDetail"] }) {
  const pay = usePayOrder(order.id);
  const triedPay = useRef(false);
  const payMutate = pay.mutate;
  const charge = order.charge;
  const pendingCharge = order.status === "pending_payment" && charge?.status === "pending";

  const needsCharge = order.status === "pending_payment" && !pendingCharge;
  useEffect(() => {
    if (needsCharge && !triedPay.current) {
      triedPay.current = true;
      payMutate(undefined, { onError: (error) => toast.error(messageOf(error)) });
    }
  }, [needsCharge, payMutate]);

  if (pendingCharge && charge.method === "CARD") {
    return (
      <Card className="flex items-start gap-3 p-5" role="status">
        <Hourglass aria-hidden className="mt-0.5 size-5 shrink-0 text-accent" />
        <div className="space-y-1">
          <p className="font-semibold">Pagamento em análise</p>
          <p className="text-sm text-muted">
            O pagamento com cartão está sendo confirmado. Esta página atualiza sozinha, e avisamos
            por e-mail assim que for aprovado.
          </p>
        </div>
      </Card>
    );
  }

  if (pendingCharge) {
    return <PixPayment charge={charge} />;
  }

  if (needsCharge) {
    if (!pay.isError) return <Skeleton className="h-72 w-full" />;
    return (
      <Card className="space-y-3 p-5 text-center" role="alert">
        <p>Não conseguimos gerar o PIX agora.</p>
        <Button
          variant="primary"
          pending={pay.isPending}
          onClick={() =>
            pay.mutate(undefined, { onError: (error) => toast.error(messageOf(error)) })
          }
        >
          Tentar de novo
        </Button>
      </Card>
    );
  }

  if (order.status === "expired") {
    return (
      <Card className="space-y-3 p-5" role="alert">
        <p className="font-semibold">O prazo do PIX terminou</p>
        <p className="text-sm text-muted">Nada foi cobrado. Seus itens continuam no carrinho.</p>
        {order.can_renew_payment ? (
          <Button
            variant="primary"
            pending={pay.isPending}
            onClick={() =>
              pay.mutate(undefined, {
                onError: (error) => {
                  toast.error(messageOf(error));
                  if (error instanceof ApiError && error.code === "order_too_old") {
                    window.location.assign("/carrinho");
                  }
                },
              })
            }
          >
            Gerar novo PIX
          </Button>
        ) : (
          <Button asChild variant="primary">
            <Link href="/carrinho">Voltar ao carrinho</Link>
          </Button>
        )}
      </Card>
    );
  }

  return null;
}
