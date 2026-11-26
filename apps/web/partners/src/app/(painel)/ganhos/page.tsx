"use client";

import { Button } from "@eumini/ui/button";
import { Card } from "@eumini/ui/card";
import { EmptyState } from "@eumini/ui/empty-state";
import { formatBRL, formatDate, formatDay } from "@eumini/ui/lib/format";
import { Skeleton } from "@eumini/ui/skeleton";
import { StatusBadge } from "@eumini/ui/status-badge";
import { useState } from "react";

import { useBalance, useEntries, usePayouts } from "@/features/earnings/hooks";
import { categoryLabel } from "@eumini/ui/lib/categories";

export default function EarningsPage() {
  const balance = useBalance();
  const payouts = usePayouts();
  const [page, setPage] = useState(1);
  const entries = useEntries(page);

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Ganhos</h1>

      <div className="grid gap-3 sm:grid-cols-2">
        <Card className="p-5">
          <p className="text-sm text-muted">A receber</p>
          {balance.data ? (
            <p className="mt-1 font-display text-3xl font-semibold tabular-nums">
              {formatBRL(balance.data.to_receive_cents)}
            </p>
          ) : (
            <Skeleton className="mt-2 h-9 w-36" />
          )}
          <p className="mt-2 text-xs text-muted">
            Soma dos pedidos postados e ajustes ainda não pagos.
          </p>
        </Card>
        <Card className="p-5">
          <p className="text-sm text-muted">Já recebido</p>
          {balance.data ? (
            <p className="mt-1 font-display text-3xl font-semibold tabular-nums">
              {formatBRL(balance.data.paid_cents)}
            </p>
          ) : (
            <Skeleton className="mt-2 h-9 w-36" />
          )}
          <p className="mt-2 text-xs text-muted">A EuMini paga por PIX, na chave da sua conta.</p>
        </Card>
      </div>

      <section aria-labelledby="extrato" className="space-y-3">
        <h2 id="extrato" className="font-display text-xl font-semibold">
          Extrato
        </h2>
        {entries.isLoading && <Skeleton className="h-24 w-full" />}
        {entries.data && entries.data.results.length === 0 && (
          <EmptyState
            title="Nada por aqui ainda"
            description="Cada pedido postado entra no extrato com o valor combinado."
          />
        )}
        {entries.data && entries.data.results.length > 0 && (
          <>
            <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
              {entries.data.results.map((entry) => (
                <li key={entry.id} className="flex items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">
                      {entry.kind === "earning"
                        ? `Pedido ${entry.order_number}`
                        : "Ajuste da EuMini"}
                    </p>
                    <p className="text-sm text-muted">
                      {formatDate(entry.created_at)}
                      {entry.kind === "earning" &&
                        `, ${categoryLabel(entry.category)} ${entry.size_label}, ${entry.quantity} ${entry.quantity === 1 ? "unidade" : "unidades"}`}
                      {entry.note && `, ${entry.note}`}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span
                      className={`font-semibold tabular-nums ${entry.amount_cents < 0 ? "text-danger" : ""}`}
                    >
                      {formatBRL(entry.amount_cents)}
                    </span>
                    <StatusBadge
                      label={entry.is_paid ? "Pago" : "A receber"}
                      tone={entry.is_paid ? "success" : "neutral"}
                    />
                  </div>
                </li>
              ))}
            </ul>
            {(entries.data.previous || entries.data.next) && (
              <div className="flex justify-between">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!entries.data.previous}
                  onClick={() => setPage((current) => current - 1)}
                >
                  Anteriores
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!entries.data.next}
                  onClick={() => setPage((current) => current + 1)}
                >
                  Mais antigos
                </Button>
              </div>
            )}
          </>
        )}
      </section>

      <section aria-labelledby="repasses" className="space-y-3">
        <h2 id="repasses" className="font-display text-xl font-semibold">
          Repasses recebidos
        </h2>
        {payouts.isLoading && <Skeleton className="h-16 w-full" />}
        {payouts.data && payouts.data.results.length === 0 && (
          <p className="text-sm text-muted">Nenhum repasse ainda.</p>
        )}
        {payouts.data && payouts.data.results.length > 0 && (
          <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
            {payouts.data.results.map((payout) => (
              <li key={payout.id} className="flex items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">PIX em {formatDay(payout.paid_on)}</p>
                  <p className="text-sm text-muted">
                    {payout.entry_count} {payout.entry_count === 1 ? "lançamento" : "lançamentos"}
                    {payout.note && `, ${payout.note}`}
                  </p>
                </div>
                <span className="font-semibold tabular-nums">{formatBRL(payout.amount_cents)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
