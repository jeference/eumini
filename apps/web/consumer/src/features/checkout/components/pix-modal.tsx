"use client";

import { Skeleton } from "@kubo/ui/skeleton";
import * as Dialog from "@radix-ui/react-dialog";
import { ChevronLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { OrderPayment } from "@/features/orders/components/order-payment";
import { useOrder } from "@/features/orders/hooks";

/**
 * Pagamento do PIX por cima da etapa Pagar. "Voltar" fecha e devolve o cliente ao
 * checkout; o pedido continua o mesmo e reabrir mostra o mesmo PIX. Fica montado
 * enquanto o pedido existe, mesmo fechado, para seguir para a página do pedido assim
 * que o pagamento cair.
 */
export function PixModal({
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
        <Dialog.Overlay className="fixed inset-0 z-40 animate-fade-in bg-black/50 backdrop-blur-sm" />
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed inset-x-0 bottom-0 z-50 flex max-h-[92dvh] animate-fade-in flex-col overflow-y-auto rounded-t-3xl bg-background p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] shadow-float sm:p-6 lg:inset-x-auto lg:bottom-auto lg:left-1/2 lg:top-1/2 lg:w-full lg:max-w-2xl lg:-translate-x-1/2 lg:-translate-y-1/2 lg:rounded-3xl"
        >
          <div className="mb-5 flex items-center gap-3">
            <Dialog.Close asChild>
              <button
                type="button"
                className="flex h-9 items-center gap-1 rounded-full border-2 border-stroke bg-surface pl-2 pr-3.5 text-[13px] font-semibold transition-colors hover:border-stroke-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                <ChevronLeft aria-hidden className="size-4" />
                Voltar
              </button>
            </Dialog.Close>
            <Dialog.Title className="font-display text-lg font-semibold">
              Pague com Pix
            </Dialog.Title>
          </div>
          {!order || settled ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <OrderPayment order={order} bare />
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
