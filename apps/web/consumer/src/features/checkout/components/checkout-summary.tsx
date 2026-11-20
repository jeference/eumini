"use client";

import type { Schemas } from "@kubo/api-client";
import { Card } from "@kubo/ui/card";
import { formatBRL } from "@kubo/ui/lib/format";
import { cn } from "@kubo/ui/lib/utils";

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

/**
 * Resumo do pedido, sempre aberto. No desktop fica ao lado das etapas; no celular, só
 * na etapa Pagamento (`className` decide onde aparece).
 */
export function CheckoutSummary({ className, ...props }: SummaryProps & { className?: string }) {
  return (
    <Card asChild className={cn("space-y-4 p-5", className)}>
      <aside aria-label="Resumo do pedido">
        <h2 className="font-display text-lg font-semibold">Resumo</h2>
        <SummaryLines {...props} />
      </aside>
    </Card>
  );
}
