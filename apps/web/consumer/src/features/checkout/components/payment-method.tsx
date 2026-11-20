"use client";

import { Card } from "@kubo/ui/card";
import { Checkbox } from "@kubo/ui/checkbox";
import { RadioCard } from "@kubo/ui/radio-card";
import { CreditCard, type LucideIcon, QrCode } from "lucide-react";
import Link from "next/link";
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
 * Escolha da forma de pagamento: nada vem marcado, e cartão aparece como "Em breve".
 * `error`: tentou concluir sem escolher. `children` aparece abaixo das opções (termos).
 */
export function PaymentMethodPicker({
  pixChosen,
  onChoosePix,
  error,
  children,
}: {
  pixChosen: boolean;
  onChoosePix: () => void;
  error: boolean;
  children?: ReactNode;
}) {
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
            checked={pixChosen}
            onSelect={onChoosePix}
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
        {error && (
          <p className="mt-2 text-xs font-medium text-danger" role="alert">
            Escolha a forma de pagamento.
          </p>
        )}
        {children && <div className="mt-5 space-y-5">{children}</div>}
      </fieldset>
    </Card>
  );
}

/** Aceite exigido para criar o pedido. */
export function TermsCheckbox({
  checked,
  onChange,
  error,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  error: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Checkbox
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        aria-invalid={error}
        aria-describedby={error ? "termos-erro" : undefined}
      >
        Li e aceito os{" "}
        <Link href="/termos" target="_blank" className="underline">
          Termos de Uso
        </Link>{" "}
        e a{" "}
        <Link href="/trocas" target="_blank" className="underline">
          Política de Trocas
        </Link>
        . Sei que a peça impressa pode ter diferenças de cor e detalhe em relação à prévia.
      </Checkbox>
      {error && (
        <p id="termos-erro" className="pl-7 text-xs font-medium text-danger" role="alert">
          Para continuar, marque que leu e aceita os termos.
        </p>
      )}
    </div>
  );
}
