import { z } from "zod";

const digits = (value: string) => value.replace(/\D/g, "");

export function isValidCpf(value: string): boolean {
  const cpf = digits(value);
  if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;
  for (const length of [9, 10]) {
    let total = 0;
    for (let i = 0; i < length; i += 1) total += Number(cpf[i]) * (length + 1 - i);
    const digit = ((total * 10) % 11) % 10;
    if (digit !== Number(cpf[length])) return false;
  }
  return true;
}

/** Validação para a experiência. A autoridade continua sendo o backend. */
export const checkoutSchema = z.object({
  email: z.string().email("Informe um e-mail válido."),
  name: z.string().trim().min(3, "Informe seu nome completo."),
  cpf: z.string().refine(isValidCpf, "Informe um CPF válido."),
  phone: z
    .string()
    .refine((v) => [10, 11].includes(digits(v).length), "Informe o telefone com DDD."),
  postal_code: z.string().refine((v) => digits(v).length === 8, "Informe um CEP válido."),
  street: z.string().trim().min(2, "Informe a rua."),
  number: z.string().trim().min(1, "Informe o número."),
  complement: z.string().optional(),
  neighborhood: z.string().trim().min(2, "Informe o bairro."),
  city: z.string().trim().min(2, "Informe a cidade."),
  state: z
    .string()
    .trim()
    .regex(/^[A-Za-z]{2}$/, "Use a sigla, como SP."),
});

export type CheckoutValues = z.infer<typeof checkoutSchema>;

export const STEPS = ["dados", "entrega", "revisar", "pagar"] as const;
export type Step = (typeof STEPS)[number];
/** Etapas com campos do formulário. */
export type FormStep = "dados" | "entrega";

/** Campos validados ao sair de cada etapa. Revisar só tem o aceite; Pagar só existe com pedido. */
export const STEP_FIELDS = {
  dados: ["email", "name", "cpf", "phone"],
  entrega: ["postal_code", "street", "number", "complement", "neighborhood", "city", "state"],
} as const satisfies Record<FormStep, readonly (keyof CheckoutValues)[]>;

/** Etapa onde o campo é preenchido, para levar o cliente até um erro do backend. */
export function stepOfField(field: string): FormStep | null {
  if ((STEP_FIELDS.dados as readonly string[]).includes(field)) return "dados";
  if ((STEP_FIELDS.entrega as readonly string[]).includes(field)) return "entrega";
  return null;
}

/**
 * Primeira etapa que ainda tem campo inválido; `revisar` quando dados e entrega estão ok.
 * Nunca devolve `pagar`: essa etapa só abre depois que o pedido existe.
 */
export function firstIncompleteStep(values: Partial<CheckoutValues>): Exclude<Step, "pagar"> {
  const result = checkoutSchema.safeParse(values);
  if (result.success) return "revisar";
  const fields = result.error.issues.map((issue) => String(issue.path[0]));
  return fields.some((field) => stepOfField(field) === "dados") ? "dados" : "entrega";
}
