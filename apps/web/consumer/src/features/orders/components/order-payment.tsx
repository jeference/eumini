"use client";

import { ApiError, type Schemas } from "@kubo/api-client";
import { Button } from "@kubo/ui/button";
import { Card } from "@kubo/ui/card";
import { Skeleton } from "@kubo/ui/skeleton";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { toast } from "sonner";

import { PixPayment } from "@/features/orders/components/pix-payment";
import { usePayOrder } from "@/features/orders/hooks";
import { messageOf } from "@/lib/errors";

/**
 * Pagamento de um pedido aguardando PIX: mostra o PIX válido, gera um se faltar
 * (uma tentativa automática) e oferece um novo quando o prazo termina.
 * Fora de `pending_payment` e `expired`, não mostra nada.
 *
 * `autoGenerate={false}`: quem usa decide quando gerar (o checkout tem o botão
 * "Gerar QR Code"); sem PIX válido, não mostra nada.
 */
export function OrderPayment({
  order,
  autoGenerate = true,
}: {
  order: Schemas["OrderDetail"];
  autoGenerate?: boolean;
}) {
  const pay = usePayOrder(order.id);
  const triedPay = useRef(false);
  const payMutate = pay.mutate;

  const needsCharge =
    order.status === "pending_payment" && (!order.charge || order.charge.status !== "pending");
  useEffect(() => {
    if (autoGenerate && needsCharge && !triedPay.current) {
      triedPay.current = true;
      payMutate(undefined, { onError: (error) => toast.error(messageOf(error)) });
    }
  }, [autoGenerate, needsCharge, payMutate]);

  if (order.status === "pending_payment" && order.charge?.status === "pending") {
    return <PixPayment charge={order.charge} />;
  }

  if (needsCharge) {
    if (!autoGenerate) return null;
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
