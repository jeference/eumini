"use client";

import { track } from "@kubo/analytics";
import type { Schemas } from "@kubo/api-client";
import { Button } from "@kubo/ui/button";
import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

/** Passo a passo do pagamento, com o QR Code na tela. */
const QR_STEPS = [
  'Na opção Pix, escolha "Ler QR Code".',
  "Leia o QR Code ou, se preferir, copie o código para Pix Copia e Cola.",
  "Revise as informações e confirme o pagamento. Pronto! O status do pedido será atualizado na mesma hora.",
];

/** Sem QR Code (o gateway não mandou): só o copia e cola. */
const COPY_STEPS = [
  "Copie o código Pix.",
  'No app do seu banco, escolha "Pix Copia e Cola" e cole o código.',
  "Revise as informações e confirme o pagamento. Pronto! O status do pedido será atualizado na mesma hora.",
];

/**
 * Pagamento do PIX: QR Code, passo a passo numerado e "Copiar código Pix" na largura
 * toda. No celular, um embaixo do outro; no computador, o passo a passo ao lado do QR.
 */
export function PixPayment({ charge }: { charge: Schemas["Charge"] }) {
  const [copied, setCopied] = useState(false);
  // O código só aparece por extenso se o navegador não deixar copiar.
  const [showCode, setShowCode] = useState(false);
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
    <div className="space-y-6">
      <div className="flex flex-col items-center gap-6 sm:flex-row">
        {hasQr && (
          // eslint-disable-next-line @next/next/no-img-element -- QR Code gerado pelo gateway
          <img
            src={charge.pix_qr_base64}
            alt="QR Code do PIX"
            className="size-60 shrink-0 rounded-2xl border border-line bg-surface p-3"
          />
        )}
        <ol className="w-full min-w-0 flex-1 list-decimal space-y-3 pl-5 text-sm leading-relaxed">
          {(hasQr ? QR_STEPS : COPY_STEPS).map((text) => (
            <li key={text} className="pl-1">
              {text}
            </li>
          ))}
        </ol>
      </div>

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
    </div>
  );
}
