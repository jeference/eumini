"use client";

import { cn } from "@eumini/ui/lib/utils";
import { EmptyState } from "@eumini/ui/empty-state";
import { Skeleton } from "@eumini/ui/skeleton";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { OrderRow } from "@/features/orders/components/order-row";
import { GROUPS, TAB_ORDER, isOrderGroup } from "@/features/orders/groups";
import { type OrderGroup, useOrderSummary, useOrders } from "@/features/orders/hooks";

const EMPTY: Record<OrderGroup, string> = {
  to_print: "Nenhum pedido novo. Avisamos por e-mail quando chegar um.",
  in_production: "Nada em produção agora.",
  awaiting_label: "Nenhum pedido esperando etiqueta.",
  to_post: "Nenhuma etiqueta pronta para postar.",
  posted: "Os pedidos postados aparecem aqui.",
  cancelled: "Nenhum pedido cancelado.",
};

function Queue() {
  const router = useRouter();
  const params = useSearchParams();
  const tab = params.get("aba");
  const group: OrderGroup = isOrderGroup(tab) ? tab : "to_print";
  const summary = useOrderSummary();
  const orders = useOrders(group);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Impressões</h1>
        {summary.data && summary.data.overdue > 0 && (
          <span className="rounded-full bg-danger/10 px-3 py-1 text-sm font-semibold text-danger">
            {summary.data.overdue} {summary.data.overdue === 1 ? "atrasado" : "atrasados"}
          </span>
        )}
      </div>

      <div
        role="tablist"
        aria-label="Etapas"
        className="-mx-4 mt-5 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0"
      >
        {TAB_ORDER.map((key) => {
          const count = summary.data?.[key] ?? 0;
          const selected = key === group;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => router.replace(`/impressoes?aba=${key}`, { scroll: false })}
              className={cn(
                "inline-flex min-h-10 shrink-0 items-center gap-2 rounded-full border-2 px-4 text-sm transition-colors",
                selected
                  ? "border-accent bg-accent-soft font-semibold text-ink"
                  : "border-stroke bg-surface text-ink hover:border-stroke-hover",
              )}
            >
              {GROUPS[key].label}
              {count > 0 && (
                <span
                  className={cn(
                    "min-w-6 rounded-full px-1.5 text-xs font-semibold tabular-nums",
                    selected ? "bg-accent text-white" : "bg-sunken",
                  )}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div role="tabpanel" className="mt-5">
        {orders.isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}
        {orders.data && orders.data.results.length === 0 && (
          <EmptyState title={GROUPS[group].label} description={EMPTY[group]} />
        )}
        {orders.data && orders.data.results.length > 0 && (
          <ul className="space-y-3">
            {orders.data.results.map((order) => (
              <li key={order.id}>
                <OrderRow order={order} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function QueuePage() {
  return (
    <Suspense>
      <Queue />
    </Suspense>
  );
}
