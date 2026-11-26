"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { unwrap } from "@eumini/api-client";
import { useApiClient } from "@eumini/api-client/react";
import { Button } from "@eumini/ui/button";
import { Callout } from "@eumini/ui/callout";
import { Form, TextField } from "@eumini/ui/form";
import { useLogin } from "@eumini/web-core/auth-client";
import { handleFormError } from "@eumini/web-core/forms";
import { useMutation } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useForm } from "react-hook-form";

import { type InviteValues, inviteSchema } from "@/features/account/schemas";

function InviteForm() {
  const router = useRouter();
  const params = useSearchParams();
  const email = params.get("email") ?? "";
  const code = params.get("codigo") ?? "";
  const api = useApiClient();
  const login = useLogin();
  const form = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { password: "", confirm: "" },
  });

  const accept = useMutation({
    mutationFn: async (values: InviteValues) => {
      unwrap(
        await api.POST("/api/partner/invite/accept/", {
          body: { email, code, password: values.password },
        }),
      );
      await login.mutateAsync({ email, password: values.password });
    },
    onSuccess: () => router.replace("/impressoes"),
    onError: (error) => handleFormError(error, form.setError),
  });

  if (!email || !code) {
    return (
      <Callout tone="danger" role="alert" className="p-4">
        Este link de convite está incompleto. Abra o link do e-mail de novo ou peça um novo convite
        à EuMini.
      </Callout>
    );
  }

  return (
    <>
      <p className="mt-2 text-sm text-muted">
        Crie a senha de <strong className="text-ink">{email}</strong> para entrar no app de
        parceiros.
      </p>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((values) => accept.mutate(values))}
          noValidate
          className="mt-6 space-y-4"
        >
          <TextField
            control={form.control}
            name="password"
            label="Senha"
            type="password"
            autoComplete="new-password"
          />
          <TextField
            control={form.control}
            name="confirm"
            label="Repita a senha"
            type="password"
            autoComplete="new-password"
          />
          <Button type="submit" variant="primary" className="w-full" pending={accept.isPending}>
            Criar senha e entrar
          </Button>
        </form>
      </Form>
    </>
  );
}

export default function InvitePage() {
  return (
    <div className="mx-auto max-w-md py-8">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Boas-vindas!</h1>
      <Suspense>
        <InviteForm />
      </Suspense>
    </div>
  );
}
