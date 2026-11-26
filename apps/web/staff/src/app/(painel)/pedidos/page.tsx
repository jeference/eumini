"use client";

import type { Schemas } from "@eumini/api-client";
import { Button } from "@eumini/ui/button";
import { Input } from "@eumini/ui/input";
import { Label } from "@eumini/ui/label";
import { ORDER_STATUS } from "@eumini/ui/lib/status";
import { Skeleton } from "@eumini/ui/skeleton";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useState } from "react";

import { OrderRow } from "@/features/orders/components/order-row";
import { type OrderFilters, useOrders } from "@/features/orders/hooks";
import { usePartners } from "@/features/partners/hooks";

type OrderStatus = Schemas["OrderStatusEnum"];
const SELECT =
  "h-12 w-full rounded-2xl border-2 border-stroke bg-surface px-3 text-base focus:border-accent focus:outline-none sm:text-sm";

function Orders() {
  const router = useRouter();
  const params = useSearchParams();
  const partners = usePartners();
  const filters: OrderFilters = {
    status: (params.get("status") as OrderStatus | null) ?? undefined,
    q: params.get("q") ?? undefined,
    parceiro: params.get("parceiro") ?? undefined,
    desde: params.get("desde") ?? undefined,
    ate: params.get("ate") ?? undefined,
    page: Number(params.get("pagina") ?? "1"),
  };
  const [search, setSearch] = useState(filters.q ?? "");
  const orders = useOrders(filters);

  function update(changes: Record<string, string | undefined>) {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!("pagina" in changes)) next.delete("pagina");
    router.replace(`/pedidos?${next.toString()}`, { scroll: false });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    update({ q: search.trim() || undefined });
  }

  const page = filters.page ?? 1;

  return (
    <div className="space-y-5">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Pedidos</h1>

      <form
        onSubmit={submit}
        className="grid gap-3 rounded-2xl border border-line bg-surface p-4 shadow-card sm:grid-cols-2 lg:grid-cols-5"
      >
        <div className="space-y-1.5 lg:col-span-2">
          <Label htmlFor="busca">Número ou e-mail</Label>
          <Input
            id="busca"
            value={search}
            placeholder="EM... ou cliente@email.com"
            onChange={(event) => setSearch(event.target.value)}
            onBlur={() => update({ q: search.trim() || undefined })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="status">Status</Label>
          <select
            id="status"
            className={SELECT}
            value={filters.status ?? ""}
            onChange={(event) => update({ status: event.target.value || undefined })}
          >
            <option value="">Todos</option>
            {(Object.keys(ORDER_STATUS) as OrderStatus[]).map((key) => (
              <option key={key} value={key}>
                {ORDER_STATUS[key].label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="parceiro">Parceiro</Label>
          <select
            id="parceiro"
            className={SELECT}
            value={filters.parceiro ?? ""}
            onChange={(event) => update({ parceiro: event.target.value || undefined })}
          >
            <option value="">Todos</option>
            {partners.data?.results.map((partner) => (
              <option key={partner.id} value={partner.id}>
                {partner.name}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1.5">
            <Label htmlFor="desde">De</Label>
            <Input
              id="desde"
              type="date"
              value={filters.desde ?? ""}
              onChange={(event) => update({ desde: event.target.value || undefined })}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ate">Até</Label>
            <Input
              id="ate"
              type="date"
              value={filters.ate ?? ""}
              onChange={(event) => update({ ate: event.target.value || undefined })}
            />
          </div>
        </div>
      </form>

      <section className="space-y-3">
        {orders.isLoading && <Skeleton className="h-20 w-full" />}
        {orders.data && (
          <p className="text-sm text-muted">
            {orders.data.count} {orders.data.count === 1 ? "pedido" : "pedidos"}
          </p>
        )}
        {orders.data?.results.map((order) => (
          <OrderRow key={order.id} order={order} />
        ))}
        {orders.data && (orders.data.previous || orders.data.next) && (
          <div className="flex justify-between">
            <Button
              variant="secondary"
              size="sm"
              disabled={!orders.data.previous}
              onClick={() => update({ pagina: String(page - 1) })}
            >
              Anteriores
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={!orders.data.next}
              onClick={() => update({ pagina: String(page + 1) })}
            >
              Próximos
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}

export default function OrdersPage() {
  return (
    <Suspense>
      <Orders />
    </Suspense>
  );
}
