"use client";

import { Button } from "@eumini/ui/button";
import { Callout } from "@eumini/ui/callout";
import { Input } from "@eumini/ui/input";
import { categoryLabel } from "@eumini/ui/lib/categories";
import { formatBRL } from "@eumini/ui/lib/format";
import { Skeleton } from "@eumini/ui/skeleton";
import { handleFormError } from "@eumini/web-core/forms";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { useRates, useSaveRates } from "@/features/partners/hooks";
import { centsToInput, parseBRL } from "@/features/partners/money";

const key = (row: { category: string; size_id: string }) => `${row.category}:${row.size_id}`;

export default function RatesPage() {
  const { data: rows, isLoading } = useRates();
  const save = useSaveRates();
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (rows) {
      setValues(Object.fromEntries(rows.map((row) => [key(row), centsToInput(row.amount_cents)])));
    }
  }, [rows]);

  function submit() {
    if (!rows) return;
    const rates = [];
    for (const row of rows) {
      const text = (values[key(row)] ?? "").trim();
      const cents = text ? parseBRL(text) : null;
      if (text && (cents === null || cents <= 0)) {
        toast.error(`Valor inválido em ${categoryLabel(row.category)} ${row.size_label}.`);
        return;
      }
      rates.push({ category: row.category, size_id: row.size_id, amount_cents: cents });
    }
    save.mutate(rates, {
      onSuccess: () => toast.success("Tarifas salvas. Valem para as próximas atribuições."),
      onError: (error) => handleFormError(error),
    });
  }

  const categories = [...new Set(rows?.map((row) => row.category) ?? [])];

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Tarifas dos parceiros</h1>
      <Callout tone="neutral">
        Valor por peça que o parceiro recebe, por categoria e tamanho. O valor fica congelado na
        atribuição: mudar aqui não altera pedidos já atribuídos. Sem tarifa, o pedido não pode ser
        atribuído.
      </Callout>
      {isLoading && <Skeleton className="h-60 w-full" />}
      {categories.map((category) => (
        <section key={category} className="space-y-2">
          <h2 className="font-display text-xl font-semibold">{categoryLabel(category)}</h2>
          <div className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
            {rows
              ?.filter((row) => row.category === category)
              .map((row) => {
                const cents = parseBRL(values[key(row)] ?? "");
                const share =
                  cents && row.price_cents ? Math.round((cents / row.price_cents) * 100) : null;
                return (
                  <div key={key(row)} className="flex items-center gap-3 px-4 py-3 text-sm">
                    <span className="w-16 font-semibold">{row.size_label}</span>
                    <span className="flex-1 text-muted">
                      Venda {formatBRL(row.price_cents)}
                      {share !== null && `, parceiro ${share}%`}
                    </span>
                    <Input
                      aria-label={`Tarifa ${categoryLabel(row.category)} ${row.size_label}`}
                      inputMode="decimal"
                      placeholder="Sem tarifa"
                      className="w-32 text-right"
                      value={values[key(row)] ?? ""}
                      onChange={(event) =>
                        setValues((current) => ({ ...current, [key(row)]: event.target.value }))
                      }
                    />
                  </div>
                );
              })}
          </div>
        </section>
      ))}
      {rows && (
        <Button variant="primary" pending={save.isPending} onClick={submit}>
          Salvar tarifas
        </Button>
      )}
    </div>
  );
}
