"use client";

import { TextField } from "@eumini/ui/form";
import { formatCpf } from "@eumini/ui/lib/format";
import { useFormContext } from "react-hook-form";

import type { CheckoutValues } from "@/features/checkout/schemas";

export function ContactStep() {
  const { control } = useFormContext<CheckoutValues>();
  return (
    <div className="space-y-4">
      <TextField
        control={control}
        name="email"
        label="E-mail"
        type="email"
        autoComplete="email"
        hint="Para onde mandamos a confirmação e o acompanhamento."
      />
      <TextField control={control} name="name" label="Nome completo" autoComplete="name" />
      <TextField
        control={control}
        name="cpf"
        label="CPF"
        inputMode="numeric"
        format={formatCpf}
        hint="Para a nota fiscal e o envio."
        className="sm:max-w-xs"
      />
    </div>
  );
}
