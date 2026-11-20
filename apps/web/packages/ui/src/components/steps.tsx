import { Check } from "lucide-react";

import { cn } from "../lib/utils";

/**
 * Progresso de um fluxo em etapas: bolinha amarela na atual, check nas feitas.
 * Etapas feitas são clicáveis para voltar; as próximas só aparecem.
 */
export function Steps<T extends string>({
  steps,
  current,
  onSelect,
  className,
}: {
  steps: readonly { id: T; label: string }[];
  current: T;
  onSelect?: (id: T) => void;
  className?: string;
}) {
  const currentIndex = steps.findIndex((step) => step.id === current);
  return (
    <ol className={cn("flex items-center gap-2", className)}>
      {steps.map((step, index) => {
        const done = index < currentIndex;
        const active = index === currentIndex;
        const content = (
          <>
            <span
              className={cn(
                "flex size-7 shrink-0 items-center justify-center rounded-full text-[13px] font-semibold transition-colors",
                active && "bg-highlight text-ink",
                done && "bg-accent text-white",
                !active && !done && "border-2 border-stroke bg-surface text-muted",
              )}
            >
              {done ? <Check className="size-4" strokeWidth={3} aria-hidden /> : index + 1}
            </span>
            <span
              className={cn(
                "text-sm font-semibold",
                active ? "text-ink" : "text-muted",
                !active && "max-sm:sr-only",
              )}
            >
              {step.label}
            </span>
          </>
        );
        return (
          <li
            key={step.id}
            className={cn("flex items-center gap-2", index < steps.length - 1 && "flex-1")}
            aria-current={active ? "step" : undefined}
          >
            {done && onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(step.id)}
                className="flex items-center gap-2 rounded-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                {content}
              </button>
            ) : (
              <span className="flex items-center gap-2">{content}</span>
            )}
            {index < steps.length - 1 && (
              <span
                aria-hidden
                className={cn("h-0.5 min-w-4 flex-1 rounded-full", done ? "bg-accent" : "bg-line")}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
