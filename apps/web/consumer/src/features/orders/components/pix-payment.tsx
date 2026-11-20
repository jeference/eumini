"use client";

import { track } from "@kubo/analytics";
import type { Schemas } from "@kubo/api-client";
import { Button } from "@kubo/ui/button";
import { Card } from "@kubo/ui/card";
import { formatBRL } from "@kubo/ui/lib/format";
import { cn } from "@kubo/ui/lib/utils";
import { Check, Copy, QrCode } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

function useCountdown(expiresAt: string): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  return Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000));
}

/**
 * Pagamento do PIX. No computador o QR Code vem primeiro (escaneia com o celular);
 * no celular o copia e cola vem primeiro e o QR fica atrás de um botão.
 */
export function PixPayment({ charge }: { charge: Schemas["Charge"] }) {
  const remaining = useCountdown(charge.expires_at);
  const [copied, setCopied] = useState(false);
  const [showQr, setShowQr] = useState(false);
  // O código só aparece por extenso se o navegador não deixar copiar.
  const [showCode, setShowCode] = useState(false);
  const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
  const seconds = String(remaining % 60).padStart(2, "0");

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
      <p className="font-display text-3xl font-semibold tabular-nums">
        {formatBRL(charge.amount_cents)}
      </p>
      <Card className="flex flex-col gap-4 p-5 text-center sm:p-6">
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

        {charge.pix_qr_base64 && (
          <div
            className={cn(
              "space-y-2",
              "[@media(pointer:coarse)]:order-last",
              !showQr && "[@media(pointer:coarse)]:hidden",
            )}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- QR Code gerado pelo gateway */}
            <img
              src={charge.pix_qr_base64}
              alt="QR Code do PIX"
              className="mx-auto size-56 rounded-2xl border border-line"
            />
            <p className={"text-sm text-muted [@media(pointer:coarse)]:hidden"}>
              Abra o app do seu banco, escolha pagar com Pix e escaneie o código.
            </p>
          </div>
        )}

        <ol
          className={cn(
            "mx-auto hidden max-w-xs space-y-1.5 text-left text-sm",
            "[@media(pointer:coarse)]:block",
          )}
        >
          {["Copie o código", "Abra o app do seu banco", "Escolha Pix copia e cola e cole"].map(
            (text, index) => (
              <li key={text} className="flex items-center gap-2.5">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
                  {index + 1}
                </span>
                {text}
              </li>
            ),
          )}
        </ol>

        <div className="space-y-3">
          <Button variant="primary" size="lg" className="w-full sm:w-auto" onClick={copy}>
            {copied ? <Check /> : <Copy />}
            {copied ? "Código copiado" : "Copiar código Pix"}
          </Button>
          {showCode && (
            <p className="break-all rounded-2xl bg-sunken p-3 text-left font-mono text-xs text-muted">
              {charge.pix_br_code}
            </p>
          )}
        </div>

        {charge.pix_qr_base64 && !showQr && (
          <Button
            variant="secondary"
            size="sm"
            className={"mx-auto hidden [@media(pointer:coarse)]:inline-flex"}
            onClick={() => setShowQr(true)}
          >
            <QrCode />
            Pagar com outro celular (QR Code)
          </Button>
        )}
      </Card>
    </div>
  );
}
