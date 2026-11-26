import type { ReactNode } from "react";

import { cn } from "../lib/utils";

/** Opção de escolha única em cartão (frete, pagamento, tema): bolinha à esquerda (opcional), valor à direita. */
export function RadioCard({
  name,
  checked,
  onSelect,
  aside,
  disabled = false,
  size = "default",
  indicator = true,
  className,
  children,
}: {
  name: string;
  checked: boolean;
  onSelect: () => void;
  aside?: ReactNode;
  /** Opção visível mas indisponível (ex.: "Em breve"). */
  disabled?: boolean;
  /** `sm`: opção de uma linha só, mais baixa. */
  size?: "default" | "sm";
  /** `false`: sem a bolinha; a borda roxa já mostra a escolhida. */
  indicator?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    <label
      className={cn(
        "flex items-center justify-between gap-3 rounded-2xl border-2 transition-[background-color,border-color]",
        size === "sm" ? "px-4 py-2.5" : "p-4",
        !indicator &&
          "relative has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent",
        disabled
          ? "cursor-not-allowed border-stroke bg-surface opacity-60"
          : checked
            ? "cursor-pointer border-accent bg-accent-soft"
            : "cursor-pointer border-stroke bg-surface hover:border-stroke-hover",
        className,
      )}
    >
      <span className="flex items-center gap-3">
        <input
          type="radio"
          name={name}
          checked={checked}
          disabled={disabled}
          onChange={onSelect}
          className={cn(
            indicator
              ? "size-5 shrink-0 cursor-pointer appearance-none disabled:cursor-not-allowed rounded-full border-2 border-stroke-hover bg-surface transition-[border] checked:border-[6px] checked:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              : "sr-only",
          )}
        />
        <span>{children}</span>
      </span>
      {aside && <span className="text-sm font-semibold tabular-nums">{aside}</span>}
    </label>
  );
}
