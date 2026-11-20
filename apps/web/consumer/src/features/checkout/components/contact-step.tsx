"use client";

import { TextField } from "@kubo/ui/form";
import { formatCpf, formatPhone } from "@kubo/ui/lib/format";
import { useFormContext } from "react-hook-form";

import { ContinueButton } from "@/features/checkout/components/checkout-step";
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
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          control={control}
          name="cpf"
          label="CPF"
          inputMode="numeric"
          format={formatCpf}
          hint="Para a nota fiscal e o envio."
        />
        <TextField
          control={control}
          name="phone"
          label="Celular"
          type="tel"
          autoComplete="tel-national"
          format={formatPhone}
          hint="Só se a transportadora precisar."
        />
      </div>
      <ContinueButton />
    </div>
  );
}

/** Resumo da etapa já feita. O CPF aparece mascarado. */
export function ContactSummary({ values }: { values: CheckoutValues }) {
  const cpf = values.cpf.replace(/\D/g, "");
  return (
    <p className="space-y-0.5">
      <span className="block text-ink">{values.name}</span>
      <span className="block break-all">{values.email}</span>
      <span className="block">
        CPF •••.•••.{cpf.slice(6, 9)}-{cpf.slice(9)} · {values.phone}
      </span>
    </p>
  );
}
