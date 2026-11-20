"use client";

import { Button } from "@kubo/ui/button";
import { Card } from "@kubo/ui/card";
import { cn } from "@kubo/ui/lib/utils";
import { Check } from "lucide-react";
import { type ReactNode, useEffect, useRef } from "react";

export type StepState = "open" | "done" | "todo";

/**
 * Uma etapa do checkout em acordeão: aberta mostra o conteúdo, feita vira um
 * resumo com "Alterar", e as próximas aparecem só com o título.
 */
export function CheckoutStep({
  number,
  title,
  state,
  summary,
  onEdit,
  children,
}: {
  number: number;
  title: string;
  state: StepState;
  summary?: ReactNode;
  onEdit?: () => void;
  children: ReactNode;
}) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const wasOpen = useRef(state === "open");

  // Ao abrir (não no primeiro render), leva a etapa para a tela e o foco para o título.
  useEffect(() => {
    if (state === "open" && !wasOpen.current) {
      const heading = headingRef.current;
      heading?.focus({ preventScroll: true });
      heading?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    wasOpen.current = state === "open";
  }, [state]);

  return (
    <Card asChild className={cn("p-5 sm:p-6", state === "todo" && "shadow-none")}>
      <section aria-labelledby={`etapa-${number}`}>
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className={cn(
              "flex size-7 shrink-0 items-center justify-center rounded-full text-[13px] font-semibold",
              state === "open" && "bg-highlight text-ink",
              state === "done" && "bg-accent text-white",
              state === "todo" && "border-2 border-stroke text-muted",
            )}
          >
            {state === "done" ? <Check className="size-4" strokeWidth={3} /> : number}
          </span>
          <h2
            ref={headingRef}
            id={`etapa-${number}`}
            tabIndex={-1}
            className={cn(
              "flex-1 scroll-mt-6 font-display text-lg font-semibold outline-none",
              state === "todo" && "text-muted",
            )}
          >
            {title}
          </h2>
          {state === "done" && onEdit && (
            <Button type="button" variant="secondary" size="sm" onClick={onEdit}>
              Alterar
            </Button>
          )}
        </div>
        {state === "done" && summary && (
          <div className="mt-2 pl-10 text-sm text-muted">{summary}</div>
        )}
        {state === "open" && <div className="mt-5">{children}</div>}
      </section>
    </Card>
  );
}
