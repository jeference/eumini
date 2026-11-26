"use client";

import { cn } from "@eumini/ui/lib/utils";
import { Skeleton } from "@eumini/ui/skeleton";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { OrderRow } from "@/features/orders/components/order-row";
import { useOrders, useQueueSummary } from "@/features/orders/hooks";
import { QUEUE_ORDER, QUEUES, type Queue } from "@/features/orders/labels";

function isQueue(value: string | null): value is Queue {
  return value !== null && (QUEUE_ORDER as string[]).includes(value);
}

function Today() {
  const router = useRouter();
  const params = useSearchParams();
  const summary = useQueueSummary();
  const fromUrl = params.get("fila");
  // Sem escolha na URL, abre o primeiro grupo que tem pedido.
  const firstWithOrders = QUEUE_ORDER.find((key) => (summary.data?.[key] ?? 0) > 0);
  const queue: Queue = isQueue(fromUrl) ? fromUrl : (firstWithOrders ?? "to_assign");
  const orders = useOrders({ fila: queue });

  return (
    <div className="space-y-5">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Hoje</h1>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        {QUEUE_ORDER.map((key) => {
          const count = summary.data?.[key];
          const selected = key === queue;
          const alarming = key !== "to_deliver" && (count ?? 0) > 0;
          return (
            <button
              key={key}
              type="button"
              aria-pressed={selected}
              onClick={() => router.replace(`/hoje?fila=${key}`, { scroll: false })}
              className={cn(
                "rounded-2xl border-2 bg-surface p-4 text-left shadow-card transition-colors",
                selected ? "border-accent" : "border-transparent hover:border-stroke",
              )}
            >
              <span className="block text-sm font-semibold">{QUEUES[key].label}</span>
              {count === undefined ? (
                <Skeleton className="mt-2 h-8 w-10" />
              ) : (
                <span
                  className={cn(
                    "mt-1 block font-display text-3xl font-semibold tabular-nums",
                    alarming && "text-accent",
                  )}
                >
                  {count}
                </span>
              )}
              <span className="mt-1 block text-xs text-muted">{QUEUES[key].hint}</span>
            </button>
          );
        })}
      </div>

      <section aria-label={QUEUES[queue].label} className="space-y-3">
        {orders.isLoading && <Skeleton className="h-20 w-full" />}
        {orders.data && orders.data.results.length === 0 && (
          <p className="rounded-2xl bg-sunken px-4 py-8 text-center text-sm text-muted">
            {QUEUES[queue].empty}
          </p>
        )}
        {orders.data?.results.map((order) => (
          <OrderRow key={order.id} order={order} />
        ))}
      </section>
    </div>
  );
}

export default function TodayPage() {
  return (
    <Suspense>
      <Today />
    </Suspense>
  );
}
