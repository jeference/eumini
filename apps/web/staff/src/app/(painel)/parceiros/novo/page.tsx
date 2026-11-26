"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@eumini/ui/button";
import { Card } from "@eumini/ui/card";
import { Form, TextField } from "@eumini/ui/form";
import { formatCep } from "@eumini/ui/lib/format";
import { handleFormError } from "@eumini/web-core/forms";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { type PartnerValues, partnerSchema } from "@/features/account/schemas";
import { useCreatePartner } from "@/features/partners/hooks";

export default function NewPartnerPage() {
  const router = useRouter();
  const create = useCreatePartner();
  const form = useForm<PartnerValues>({
    resolver: zodResolver(partnerSchema),
    defaultValues: { name: "", email: "", origin_postal_code: "", pix_key: "" },
  });

  function onSubmit(values: PartnerValues) {
    const parsed = partnerSchema.parse(values);
    create.mutate(parsed, {
      onSuccess: (partner) => {
        toast.success(`Convite enviado para ${partner.login_email}.`);
        router.replace(`/parceiros/${partner.id}`);
      },
      onError: (error) => handleFormError(error, form.setError),
    });
  }

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Novo parceiro</h1>
      <Card className="p-5">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} noValidate className="space-y-4">
            <TextField control={form.control} name="name" label="Nome" autoComplete="off" />
            <TextField
              control={form.control}
              name="email"
              label="E-mail do login"
              type="email"
              hint="O convite para criar a senha vai para este e-mail."
            />
            <TextField
              control={form.control}
              name="origin_postal_code"
              label="CEP de onde ele posta"
              inputMode="numeric"
              format={formatCep}
            />
            <TextField
              control={form.control}
              name="pix_key"
              label="Chave PIX para os repasses"
              hint="Opcional agora. Precisa estar preenchida no primeiro repasse."
            />
            <Button type="submit" variant="primary" className="w-full" pending={create.isPending}>
              Cadastrar e enviar convite
            </Button>
          </form>
        </Form>
      </Card>
    </div>
  );
}
