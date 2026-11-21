"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Cartão pelo abacatepay.js: o SDK desenha os campos num iframe dele (o número e o CVV nunca
 * passam pelo nosso código) e o `tokenize()` devolve um `ctok_` que vale 60 s, serve para uma só
 * cobrança e fica preso ao valor. Se o banco pedir 3DS, o modal é do próprio SDK. Com chave
 * de teste, o SDK mostra campos simples já preenchidos (devMock), sem o provedor real.
 */

const SDK_URL = "https://abacatepay.com/abacatepay.js";
const PUBLIC_KEY = process.env.NEXT_PUBLIC_ABACATEPAY_PUBLIC_KEY ?? "";

/** Sem chave configurada, o cartão continua "Em breve". */
export const CARD_ENABLED = PUBLIC_KEY.startsWith("pk_");

type SdkError = { code?: string; message?: string };

type SdkCheckout = {
  mount: (selector: string) => Promise<unknown>;
  /** Resolve com o token; rejeita com `{code, message}`. */
  tokenize: (customer: CardCustomer) => Promise<{ token: string }>;
  destroy: () => void;
};

type Sdk = {
  create: (options: {
    publicKey: string;
    amount: number;
    locale?: "pt" | "en" | "es";
    icons?: boolean;
    onReady?: () => void;
    onCardChange?: (state: { canTokenize: boolean }) => void;
  }) => SdkCheckout;
};

declare global {
  interface Window {
    AbacatePay?: Sdk;
  }
}

export type CardCustomer = { name: string; email: string; taxId: string; cellphone: string };

/** Erro do formulário do cartão, já com a mensagem para o cliente. */
export class CardError extends Error {
  constructor(
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

const MESSAGES: Record<string, string> = {
  CARD_INCOMPLETE: "Preencha os dados do cartão.",
  CARD_INVALID: "Confira os dados do cartão.",
  THREE_DS_FAILED:
    "O banco não confirmou o cartão. Tente de novo, use outro cartão ou pague com Pix.",
  NETWORK: "Sem conexão com o pagamento. Confira a internet e tente de novo.",
};

function toCardError(error: SdkError | undefined): CardError {
  const code = error?.code ?? "UNKNOWN";
  return new CardError(
    code,
    MESSAGES[code] ?? "Não foi possível validar o cartão. Tente de novo ou pague com Pix.",
  );
}

let sdkPromise: Promise<Sdk> | null = null;

/** Carrega o script uma vez por página. Se falhar, a próxima tentativa carrega de novo. */
function loadSdk(): Promise<Sdk> {
  if (window.AbacatePay) return Promise.resolve(window.AbacatePay);
  sdkPromise ??= new Promise<Sdk>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SDK_URL;
    script.async = true;
    script.onload = () =>
      window.AbacatePay ? resolve(window.AbacatePay) : reject(new Error("sdk ausente"));
    script.onerror = () => {
      script.remove();
      sdkPromise = null;
      reject(new Error("sdk não carregou"));
    };
    document.head.appendChild(script);
  });
  return sdkPromise;
}

export type CardFormStatus = "loading" | "ready" | "error";

/**
 * Monta o formulário do cartão no elemento `containerId` enquanto `enabled`. Mudar o valor
 * recria o formulário, porque o token fica preso ao valor.
 */
export function useCardForm({
  containerId,
  amount,
  enabled,
}: {
  containerId: string;
  amount: number;
  enabled: boolean;
}) {
  const [status, setStatus] = useState<CardFormStatus>("loading");
  const [canTokenize, setCanTokenize] = useState(false);
  const checkout = useRef<SdkCheckout | null>(null);

  useEffect(() => {
    if (!enabled || !CARD_ENABLED) return;
    let cancelled = false;
    setStatus("loading");
    setCanTokenize(false);

    loadSdk()
      .then(async (sdk) => {
        if (cancelled) return;
        const created = sdk.create({
          publicKey: PUBLIC_KEY,
          amount,
          locale: "pt",
          icons: true,
          onCardChange: (state) => setCanTokenize(state.canTokenize),
        });
        checkout.current = created;
        await created.mount(`#${containerId}`);
        if (!cancelled) setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
      const current = checkout.current;
      checkout.current = null;
      try {
        current?.destroy();
      } catch {
        // O iframe some junto com o container.
      }
      document.getElementById(containerId)?.replaceChildren();
    };
  }, [enabled, amount, containerId]);

  /** Gera o `ctok_`. Rejeita com `CardError` (mensagem pronta para o cliente). */
  const tokenize = useCallback(async (customer: CardCustomer): Promise<string> => {
    const current = checkout.current;
    if (!current) throw new CardError("NOT_READY", "Aguarde o formulário do cartão carregar.");
    let result: { token?: string } | undefined;
    try {
      result = await current.tokenize(customer);
    } catch (error) {
      throw toCardError(error as SdkError);
    }
    if (!result?.token) throw toCardError(undefined);
    return result.token;
  }, []);

  return { status, canTokenize, tokenize };
}
