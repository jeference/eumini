const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const DATE = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "medium",
  timeZone: "America/Sao_Paulo",
});

/** Dinheiro é sempre centavos inteiros no backend; reais só na exibição. */
export function formatBRL(cents: number): string {
  return BRL.format(cents / 100);
}

export function formatDate(value: string): string {
  return DATE.format(new Date(value));
}

/**
 * Data sem hora ("2026-11-30"), como um prazo. `new Date` leria meia-noite em UTC, que em
 * Brasília ainda é o dia anterior: aqui o dia é lido ao meio-dia de Brasília.
 */
export function formatDay(value: string): string {
  return DATE.format(new Date(`${value}T12:00:00-03:00`));
}

export function formatCep(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  return digits.length > 5 ? `${digits.slice(0, 5)}-${digits.slice(5)}` : digits;
}

export function formatCpf(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  return digits
    .replace(/^(\d{3})(\d)/, "$1.$2")
    .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1-$2");
}

export function formatPhone(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 2) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  const split = digits.length === 11 ? 7 : 6;
  return `(${digits.slice(0, 2)}) ${digits.slice(2, split)}-${digits.slice(split)}`;
}
