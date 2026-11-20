"use client";

import { Card } from "@kubo/ui/card";
import { RadioCard } from "@kubo/ui/radio-card";
import { CreditCard, type LucideIcon, QrCode } from "lucide-react";
import type { ReactNode } from "react";

import { STEP_HEADING_ID } from "@/features/checkout/components/checkout-step";

/** Nome da forma de pagamento. `note` vai numa linha pequena embaixo (cabe lado a lado no celular). */
function MethodLabel({
  icon: Icon,
  title,
  note,
}: {
  icon: LucideIcon;
  title: string;
  note?: string;
}) {
  return (
    <span className="flex items-center gap-2.5">
      <Icon aria-hidden className="size-5 shrink-0 text-accent" />
      <span>
        <span className="block text-sm font-semibold">{title}</span>
        {note && <span className="block text-[11px] font-semibold text-muted">{note}</span>}
      </span>
    </span>
  );
}

/**
 * Forma de pagamento: o Pix, única aceita hoje, já vem marcado; cartão aparece como
 * "Em breve". `children` aparece abaixo das opções.
 */
export function PaymentMethodPicker({ children }: { children?: ReactNode }) {
  return (
    <Card asChild className="p-5 sm:p-6">
      <fieldset aria-labelledby={STEP_HEADING_ID}>
        <h2
          id={STEP_HEADING_ID}
          tabIndex={-1}
          className="font-display text-lg font-semibold outline-none"
        >
          Forma de pagamento
        </h2>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <RadioCard
            name="payment_method"
            size="sm"
            indicator={false}
            checked
            onSelect={() => undefined}
          >
            <MethodLabel icon={QrCode} title="Pix" />
          </RadioCard>
          {/* Ainda não aceito: aparece para o cliente saber que vem aí. */}
          <RadioCard
            name="payment_method"
            size="sm"
            indicator={false}
            checked={false}
            onSelect={() => undefined}
            disabled
          >
            <MethodLabel icon={CreditCard} title="Crédito" note="Em breve" />
          </RadioCard>
        </div>
        {children && <div className="mt-5 space-y-5">{children}</div>}
      </fieldset>
    </Card>
  );
}
