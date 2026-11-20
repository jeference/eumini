"use client";

import { Button } from "@kubo/ui/button";
import { Callout } from "@kubo/ui/callout";
import { Checkbox } from "@kubo/ui/checkbox";
import { formatBRL } from "@kubo/ui/lib/format";
import { Lock, QrCode } from "lucide-react";
import Link from "next/link";

export function PaymentStep({
  totalCents,
  acceptTerms,
  onAcceptTerms,
  termsError,
  shippingNotice,
  pending,
}: {
  totalCents: number;
  acceptTerms: boolean;
  onAcceptTerms: (value: boolean) => void;
  termsError: boolean;
  shippingNotice: string | null;
  pending: boolean;
}) {
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3 rounded-2xl border-2 border-accent bg-accent-soft p-4">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface">
          <QrCode aria-hidden className="size-5 text-accent" />
        </span>
        <p className="min-w-0 flex-1 text-sm">
          <span className="block font-semibold">Pix</span>
          <span className="block text-muted">
            Aprovação na hora. Na próxima tela aparecem o QR Code e o código copia e cola.
          </span>
        </p>
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

      <div className="space-y-2">
        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full"
          pending={pending}
          data-testid="pay"
        >
          <Lock aria-hidden />
          Gerar Pix de {formatBRL(totalCents)}
        </Button>
        <p className="text-center text-xs text-muted">Nada é cobrado até você pagar o Pix.</p>
      </div>
    </div>
  );
}
