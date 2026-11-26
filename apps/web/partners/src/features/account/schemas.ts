import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Informe um e-mail válido."),
  password: z.string().min(1, "Informe a senha."),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const inviteSchema = z
  .object({
    password: z.string().min(8, "Use pelo menos 8 caracteres."),
    confirm: z.string(),
  })
  .refine((values) => values.password === values.confirm, {
    message: "As senhas não são iguais.",
    path: ["confirm"],
  });
export type InviteValues = z.infer<typeof inviteSchema>;
