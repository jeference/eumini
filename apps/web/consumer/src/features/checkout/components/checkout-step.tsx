import { Button } from "@kubo/ui/button";
import { Card } from "@kubo/ui/card";
import { ArrowRight, Lock } from "lucide-react";
import type { ReactNode } from "react";

/** Id do formulário do checkout: o botão de ação fica fora dele, junto do resumo. */
export const CHECKOUT_FORM_ID = "checkout-form";

/**
 * Ação da etapa: "Continuar" nas etapas de dados e entrega, "Concluir pagamento" no Pagar.
 * Fixo no rodapé do celular; no desktop, logo abaixo do resumo do pedido.
 */
export function CheckoutAction({ finish, pending }: { finish: boolean; pending: boolean }) {
  return (
    <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-background p-4 pb-[max(1rem,env(safe-area-inset-bottom))] lg:static lg:border-0 lg:bg-transparent lg:p-0">
      <Button
        type="submit"
        form={CHECKOUT_FORM_ID}
        variant="primary"
        size="lg"
        className="w-full"
        pending={pending}
      >
        {finish ? (
          <>
            <Lock aria-hidden />
            Concluir pagamento
          </>
        ) : (
          <>
            Continuar
            <ArrowRight aria-hidden />
          </>
        )}
      </Button>
    </div>
  );
}

/** Id do título da etapa aberta: recebe o foco quando o cliente troca de etapa. */
export const STEP_HEADING_ID = "etapa-titulo";

/** A etapa aberta do checkout. Só uma aparece por vez; as outras ficam no indicador. */
export function CheckoutStep({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card asChild className="p-5 sm:p-6">
      <section aria-labelledby={STEP_HEADING_ID}>
        <h2
          id={STEP_HEADING_ID}
          tabIndex={-1}
          className="font-display text-lg font-semibold outline-none"
        >
          {title}
        </h2>
        <div className="mt-5">{children}</div>
      </section>
    </Card>
  );
}
