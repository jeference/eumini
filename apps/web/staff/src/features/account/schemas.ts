import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Informe um e-mail válido."),
  password: z.string().min(1, "Informe a senha."),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const partnerSchema = z.object({
  name: z.string().trim().min(2, "Informe o nome."),
  email: z.string().email("Informe um e-mail válido."),
  origin_postal_code: z
    .string()
    .transform((value) => value.replace(/\D/g, ""))
    .refine((value) => value.length === 8, "Informe um CEP com 8 números."),
  pix_key: z.string().trim().max(140).optional().default(""),
});
export type PartnerValues = z.input<typeof partnerSchema>;
