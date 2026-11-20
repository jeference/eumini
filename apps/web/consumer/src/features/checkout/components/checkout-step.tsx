import { Button } from "@kubo/ui/button";
import { Card } from "@kubo/ui/card";
import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";

/** Avança para a próxima etapa: à direita, como o sentido do fluxo. */
export function ContinueButton({ pending = false }: { pending?: boolean }) {
  return (
    <div className="flex justify-end">
      <Button
        type="submit"
        variant="primary"
        size="lg"
        className="w-full sm:w-auto"
        pending={pending}
      >
        Continuar
        <ArrowRight aria-hidden />
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
