"use client";

import { Button } from "@kubo/ui/button";
import { Skeleton } from "@kubo/ui/skeleton";
import * as Dialog from "@radix-ui/react-dialog";
import { ChevronLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { OrderPayment } from "@/features/orders/components/order-payment";
import { useOrder } from "@/features/orders/hooks";

/**
 * Pagamento do PIX em tela cheia, por cima do checkout: parece uma página, mas é um
 * componente (sem rota). A seta de voltar fecha e devolve o cliente ao Pagamento; o pedido
 * continua o mesmo e reabrir mostra o mesmo PIX. Fica montado enquanto o pedido existe,
 * mesmo fechado, para seguir para a página do pedido assim que o pagamento cair.
 */
export function PixScreen({
  orderId,
  open,
  onClose,
}: {
  orderId: string;
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const { data: order } = useOrder(orderId);
  const settled = Boolean(order && !["pending_payment", "expired"].includes(order.status));

  useEffect(() => {
    if (settled) router.replace(`/pedidos/${orderId}`);
  }, [settled, orderId, router]);

  return (
    <Dialog.Root open={open} onOpenChange={(next) => !next && onClose()}>
      <Dialog.Portal>
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed inset-0 z-50 animate-fade-in overflow-y-auto bg-background"
        >
          <div className="mx-auto w-full max-w-3xl px-4 pb-16 pt-6 sm:px-6">
            <div className="flex items-center gap-1">
              <Dialog.Close asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Voltar para o pagamento"
                  className="-ml-2 text-ink [&_svg]:size-6"
                >
                  <ChevronLeft />
                </Button>
              </Dialog.Close>
              <Dialog.Title className="font-display text-3xl font-semibold tracking-tight">
                Pague com Pix
              </Dialog.Title>
            </div>
            <div className="mt-6">
              {!order || settled ? (
                <Skeleton className="h-72 w-full" />
              ) : (
                <OrderPayment order={order} />
              )}
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
