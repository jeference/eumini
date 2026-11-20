"use client";

import type { Schemas } from "@kubo/api-client";
import { Card } from "@kubo/ui/card";
import { formatBRL } from "@kubo/ui/lib/format";
import { cn } from "@kubo/ui/lib/utils";
import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { categoryLabel } from "@/features/catalog/categories";

type SummaryProps = {
  items: Schemas["CartItem"][];
  subtotal: number;
  /** `null` enquanto o frete não foi escolhido. */
  shippingCents: number | null;
};

function SummaryLines({ items, subtotal, shippingCents }: SummaryProps) {
  return (
    <>
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element -- imagem dinâmica */}
            <img
              src={item.image_url}
              alt=""
              className="size-14 rounded-xl bg-sunken object-contain"
            />
            <span className="min-w-0 flex-1 text-sm">
              {item.category ? `${categoryLabel(item.category)} · ` : ""}
              {item.size_label}
              <span className="block text-muted">Quantidade: {item.quantity}</span>
            </span>
            <span className="text-sm tabular-nums">{formatBRL(item.line_total_cents)}</span>
          </li>
        ))}
      </ul>
      <dl className="space-y-1.5 border-t border-line pt-3 text-sm">
        <div className="flex justify-between">
          <dt className="text-muted">Subtotal</dt>
          <dd className="tabular-nums">{formatBRL(subtotal)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted">Frete</dt>
          <dd className="tabular-nums">
            {shippingCents === null ? "Calculado na entrega" : formatBRL(shippingCents)}
          </dd>
        </div>
        <div className="flex justify-between pt-1.5 text-lg font-semibold">
          <dt>Total</dt>
          <dd className="tabular-nums" data-testid="total">
            {formatBRL(subtotal + (shippingCents ?? 0))}
          </dd>
        </div>
      </dl>
    </>
  );
}

/** Celular: barra com o total, que abre a lista de itens. */
export function CheckoutSummaryBar(props: SummaryProps) {
  const [open, setOpen] = useState(false);
  const total = props.subtotal + (props.shippingCents ?? 0);
  const count = props.items.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <Card className="overflow-hidden lg:hidden">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="resumo-celular"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-2 px-5 py-4 text-left focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent"
      >
        <span className="flex-1 text-sm font-semibold">
          Resumo do pedido
          <span className="font-normal text-muted">
            {" "}
            · {count} {count === 1 ? "item" : "itens"}
          </span>
        </span>
        <span className="font-semibold tabular-nums">{formatBRL(total)}</span>
        <ChevronDown
          aria-hidden
          className={cn("size-4 text-muted transition-transform", open && "rotate-180")}
        />
      </button>
      {open && (
        <div id="resumo-celular" className="space-y-4 border-t border-line p-5">
          <SummaryLines {...props} />
        </div>
      )}
    </Card>
  );
}

/** Desktop: painel fixo ao lado das etapas. */
export function CheckoutSummaryPanel(props: SummaryProps) {
  return (
    <Card asChild className="space-y-4 p-5 max-lg:hidden">
      <aside aria-label="Resumo do pedido">
        <h2 className="font-display text-lg font-semibold">Resumo</h2>
        <SummaryLines {...props} />
      </aside>
    </Card>
  );
}
