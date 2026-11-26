"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@eumini/ui/button";
import { Form, TextField } from "@eumini/ui/form";
import { useLogin } from "@eumini/web-core/auth-client";
import { handleFormError } from "@eumini/web-core/forms";
import { safeNext } from "@eumini/web-core/lib/safe-next";
import { useSession } from "@eumini/web-core/session";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { useForm } from "react-hook-form";

import { type LoginValues, loginSchema } from "@/features/account/schemas";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"), "/hoje");
  const status = useSession((state) => state.status);
  const login = useLogin();
  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  useEffect(() => {
    if (status === "authenticated") router.replace(next);
  }, [status, next, router]);

  return (
    <div className="mx-auto max-w-md py-8">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Entrar</h1>
      <p className="mt-2 text-sm text-muted">Área da equipe EuMini.</p>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit((values) =>
            login.mutate(values, { onError: (error) => handleFormError(error, form.setError) }),
          )}
          noValidate
          className="mt-6 space-y-4"
        >
          <TextField
            control={form.control}
            name="email"
            label="E-mail"
            type="email"
            autoComplete="email"
          />
          <TextField
            control={form.control}
            name="password"
            label="Senha"
            type="password"
            autoComplete="current-password"
          />
          <Button type="submit" variant="primary" className="w-full" pending={login.isPending}>
            Entrar
          </Button>
        </form>
      </Form>
      <div className="mt-5 flex justify-end text-sm">
        <Link href="/recuperar-senha" className="text-muted underline">
          Primeiro acesso ou esqueci a senha
        </Link>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
