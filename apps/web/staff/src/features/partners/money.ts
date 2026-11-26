/** Soma, em centavos, dos lançamentos escolhidos para um repasse. */
export function selectedTotal(
  entries: { id: string; amount_cents: number }[],
  selected: ReadonlySet<string>,
): number {
  return entries.reduce(
    (sum, entry) => (selected.has(entry.id) ? sum + entry.amount_cents : sum),
    0,
  );
}

/**
 * Lê um valor em reais digitado ("129,90", "R$ 1.299,90", "-5") e devolve centavos.
 * Devolve null se não for um número.
 */
export function parseBRL(value: string): number | null {
  const clean = value.replace(/[R$\s.]/g, "").replace(",", ".");
  if (!/^-?\d+(\.\d{1,2})?$/.test(clean)) return null;
  return Math.round(Number(clean) * 100);
}

/** Centavos para o campo de texto: 12990 vira "129,90". */
export function centsToInput(cents: number | null | undefined): string {
  if (cents === null || cents === undefined) return "";
  return (cents / 100).toFixed(2).replace(".", ",");
}
