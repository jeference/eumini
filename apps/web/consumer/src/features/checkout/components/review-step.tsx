"use client";

import { Button } from "@kubo/ui/button";
import { Callout } from "@kubo/ui/callout";
import { Checkbox } from "@kubo/ui/checkbox";
import Link from "next/link";
import type { ReactNode } from "react";

import { ContinueButton } from "@/features/checkout/components/checkout-step";

/** Bloco consolidado de uma etapa já feita, com o atalho para voltar e alterar. */
function ReviewBlock({
  title,
  onEdit,
  children,
}: {
  title: string;
  onEdit?: () => void;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border-2 border-stroke p-4">
      <div className="flex items-center gap-3">
        <h3 className="flex-1 text-sm font-semibold">{title}</h3>
        {onEdit && (
          <Button type="button" variant="secondary" size="sm" onClick={onEdit}>
            Alterar
          </Button>
        )}
      </div>
      <div className="mt-1.5 text-sm text-muted">{children}</div>
    </div>
  );
}

export function ReviewStep({
  contact,
  delivery,
  onEditContact,
  onEditDelivery,
  acceptTerms,
  onAcceptTerms,
  termsError,
  shippingNotice,
  pending,
}: {
  contact: ReactNode;
  delivery: ReactNode;
  onEditContact: () => void;
  onEditDelivery: () => void;
  acceptTerms: boolean;
  onAcceptTerms: (value: boolean) => void;
  termsError: boolean;
  shippingNotice: string | null;
  pending: boolean;
}) {
  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <ReviewBlock title="Seus dados" onEdit={onEditContact}>
          {contact}
        </ReviewBlock>
        <ReviewBlock title="Entrega" onEdit={onEditDelivery}>
          {delivery}
        </ReviewBlock>
      </div>

      {shippingNotice && (
        <Callout tone="accent" role="alert">
          {shippingNotice}
        </Callout>
      )}

      <div className="space-y-1.5">
        <Checkbox
          checked={acceptTerms}
          onChange={(event) => onAcceptTerms(event.target.checked)}
          aria-invalid={termsError}
          aria-describedby={termsError ? "termos-erro" : undefined}
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
        {termsError && (
          <p id="termos-erro" className="pl-7 text-xs font-medium text-danger" role="alert">
            Para continuar, marque que leu e aceita os termos.
          </p>
        )}
      </div>

      <ContinueButton pending={pending} />
    </div>
  );
}
