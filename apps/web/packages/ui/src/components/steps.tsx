import { Check } from "lucide-react";

import { cn } from "../lib/utils";

/**
 * Progresso de um fluxo em etapas, com o rótulo abaixo de cada bolinha. Neutro, para não
 * tirar o foco do conteúdo: atual com contorno roxo, próximas com contorno claro, e o
 * check das feitas em roxo.
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
    <ol className={cn("flex items-start", className)}>
      {steps.map((step, index) => {
        const done = index < currentIndex;
        const active = index === currentIndex;
        const content = (
          <>
            <span
              className={cn(
                "relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full text-[13px] font-semibold transition-colors",
                "border-2 bg-surface",
                active && "border-accent text-accent",
                done && "border-stroke text-accent",
                !active && !done && "border-stroke text-muted",
              )}
            >
              {done ? <Check className="size-4" strokeWidth={3} aria-hidden /> : index + 1}
            </span>
            <span className={cn("text-xs font-semibold", active ? "text-accent" : "text-muted")}>
              {step.label}
            </span>
          </>
        );
        return (
          <li
            key={step.id}
            className="relative flex flex-1 flex-col items-center"
            aria-current={active ? "step" : undefined}
          >
            {/* Linha até a próxima bolinha, passando por trás delas. */}
            {index < steps.length - 1 && (
              <span
                aria-hidden
                className="absolute left-1/2 top-3.5 h-0.5 w-full -translate-y-1/2 bg-line"
              />
            )}
            {done && onSelect ? (
              <button
                type="button"
                onClick={() => onSelect(step.id)}
                className="flex flex-col items-center gap-1.5 rounded-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                {content}
              </button>
            ) : (
              <span className="flex flex-col items-center gap-1.5">{content}</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
