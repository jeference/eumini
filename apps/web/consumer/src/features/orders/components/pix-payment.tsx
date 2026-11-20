"use client";

import { track } from "@kubo/analytics";
import type { Schemas } from "@kubo/api-client";
import { Button } from "@kubo/ui/button";
import { Card } from "@kubo/ui/card";
import { formatBRL } from "@kubo/ui/lib/format";
import { cn } from "@kubo/ui/lib/utils";
import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

/** Computador: paga escaneando o QR com o celular, ou copiando o código. */
const QR_STEPS = [
  'Na opção Pix, escolha "Ler QR Code".',
  "Leia o QR Code ou, se preferir, copie o código para Pix Copia e Cola.",
  "Revise as informações e confirme o pagamento. Pronto! O status do pedido será atualizado na mesma hora.",
];

/** Celular: não dá para escanear a própria tela, então é só o copia e cola. */
const COPY_STEPS = [
  "Copie o código Pix",
  "Abra o app do seu banco",
  "Escolha Pix Copia e Cola e cole o código",
];

function useCountdown(expiresAt: string): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000));
}

function StepList({ steps, className }: { steps: string[]; className?: string }) {
  return (
    <ol className={cn("space-y-2.5 text-sm", className)}>
      {steps.map((text, index) => (
        <li key={text} className="flex items-start gap-2.5">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
            {index + 1}
          </span>
          <span className="pt-0.5">{text}</span>
        </li>
      ))}
    </ol>
  );
}

/**
 * Pagamento do PIX. No computador, QR Code à esquerda e passo a passo à direita.
 * No celular (toque), nada de QR: só o passo a passo do copia e cola.
 */
export function PixPayment({ charge }: { charge: Schemas["Charge"] }) {
  const remaining = useCountdown(charge.expires_at);
  const [copied, setCopied] = useState(false);
  // O código só aparece por extenso se o navegador não deixar copiar.
  const [showCode, setShowCode] = useState(false);
  const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
  const seconds = String(remaining % 60).padStart(2, "0");
  const hasQr = Boolean(charge.pix_qr_base64);

  async function copy() {
    try {
      await navigator.clipboard.writeText(charge.pix_br_code);
      setCopied(true);
      track("pix_copied");
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setShowCode(true);
      toast.error("Não foi possível copiar. Selecione o código abaixo.");
    }
  }

  return (
    <div className="space-y-3">
      <Card className="space-y-5 p-5 sm:p-6">
        <p className="text-sm text-muted">
          {remaining > 0 ? (
            <>
              O código expira em{" "}
              <span className="font-mono font-medium text-ink" data-testid="pix-countdown">
                {minutes}:{seconds}
              </span>
            </>
          ) : (
            "Este código venceu. Estamos conferindo o pagamento."
          )}
        </p>

        <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
          {hasQr && (
            // eslint-disable-next-line @next/next/no-img-element -- QR Code gerado pelo gateway
            <img
              src={charge.pix_qr_base64}
              alt="QR Code do PIX"
              className="mx-auto size-56 shrink-0 rounded-2xl border border-line sm:mx-0 [@media(pointer:coarse)]:hidden"
            />
          )}

          <div className="min-w-0 flex-1">
            {hasQr && <StepList steps={QR_STEPS} className="[@media(pointer:coarse)]:hidden" />}
            <StepList
              steps={COPY_STEPS}
              className={cn(hasQr && "hidden [@media(pointer:coarse)]:block")}
            />
          </div>
        </div>

        {/* Abaixo do QR e das instruções, na largura dos dois. */}
        <div className="space-y-3">
          <Button variant="primary" size="lg" className="w-full" onClick={copy}>
            {copied ? <Check /> : <Copy />}
            {copied ? "Código copiado" : "Copiar código Pix"}
          </Button>
          {showCode && (
            <p className="break-all rounded-2xl bg-sunken p-3 font-mono text-xs text-muted">
              {charge.pix_br_code}
            </p>
          )}
        </div>
      </Card>
      <p className="font-display text-3xl font-semibold tabular-nums">
        {formatBRL(charge.amount_cents)}
      </p>
    </div>
  );
}
