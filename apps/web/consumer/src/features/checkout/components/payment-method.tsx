"use client";

import { Card } from "@kubo/ui/card";
import { Input } from "@kubo/ui/input";
import { Label } from "@kubo/ui/label";
import { formatPhone } from "@kubo/ui/lib/format";
import { RadioCard } from "@kubo/ui/radio-card";
import { Skeleton } from "@kubo/ui/skeleton";
import { CreditCard, Lock, type LucideIcon, QrCode } from "lucide-react";
import { type ReactNode, useId } from "react";

import { CARD_ENABLED, type CardFormStatus } from "@/features/checkout/abacatepay";
import { STEP_HEADING_ID } from "@/features/checkout/components/checkout-step";

export type PaymentMethod = "pix" | "card";

/** Elemento onde o abacatepay.js desenha os campos do cartão. */
export const CARD_CONTAINER_ID = "cartao-abacatepay";

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
 * Forma de pagamento: Pix (marcado de início) ou Crédito. Sem a chave do AbacatePay
 * configurada, o Crédito aparece como "Em breve". `children` aparece abaixo das opções.
 */
export function PaymentMethodPicker({
  value,
  onChange,
  children,
}: {
  value: PaymentMethod;
  onChange: (method: PaymentMethod) => void;
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
            checked={value === "pix"}
            onSelect={() => onChange("pix")}
          >
            <MethodLabel icon={QrCode} title="Pix" />
          </RadioCard>
          <RadioCard
            name="payment_method"
            size="sm"
            indicator={false}
            checked={value === "card"}
            onSelect={() => onChange("card")}
            disabled={!CARD_ENABLED}
          >
            <MethodLabel
              icon={CreditCard}
              title="Crédito"
              note={CARD_ENABLED ? undefined : "Em breve"}
            />
          </RadioCard>
        </div>
        {children && <div className="mt-5 space-y-5">{children}</div>}
      </fieldset>
    </Card>
  );
}

/**
 * Campos do cartão (iframe do AbacatePay) e o celular, que o cartão exige. O celular só vai
 * para o gateway; não fica no pedido.
 */
export function CardPayment({
  status,
  cellphone,
  onCellphoneChange,
  cellphoneError,
  error,
}: {
  status: CardFormStatus;
  cellphone: string;
  onCellphoneChange: (value: string) => void;
  cellphoneError: string | null;
  error: string | null;
}) {
  const phoneId = useId();
  return (
    <div className="space-y-4">
      <div className="relative">
        {/* O SDK desenha aqui. Fica sempre no DOM para o mount achar o elemento. */}
        <div id={CARD_CONTAINER_ID} className={status === "ready" ? undefined : "min-h-40"} />
        {status === "loading" && <Skeleton className="absolute inset-0" />}
        {status === "error" && (
          <p
            role="alert"
            className="absolute inset-0 flex items-center justify-center rounded-2xl bg-sunken p-4 text-center text-sm text-muted"
          >
            Não conseguimos carregar o formulário do cartão. Recarregue a página ou pague com Pix.
          </p>
        )}
      </div>

      <div className="space-y-1.5 sm:max-w-xs">
        <Label htmlFor={phoneId}>Celular</Label>
        <Input
          id={phoneId}
          type="tel"
          inputMode="numeric"
          autoComplete="tel-national"
          value={cellphone}
          onChange={(event) => onCellphoneChange(formatPhone(event.target.value))}
          aria-invalid={Boolean(cellphoneError)}
          aria-describedby={cellphoneError ? `${phoneId}-error` : `${phoneId}-hint`}
        />
        {cellphoneError ? (
          <p id={`${phoneId}-error`} className="text-xs font-medium text-danger">
            {cellphoneError}
          </p>
        ) : (
          <p id={`${phoneId}-hint`} className="text-xs text-muted">
            A operadora do cartão pede um celular com DDD.
          </p>
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm font-medium text-danger">
          {error}
        </p>
      )}

      <p className="flex items-center gap-1.5 text-xs text-muted">
        <Lock aria-hidden className="size-3.5" />
        Pagamento à vista, processado pelo AbacatePay. Não guardamos os dados do cartão.
      </p>
    </div>
  );
}
