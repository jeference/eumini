"use client";

import { unwrap } from "@eumini/api-client";
import { useApiClient } from "@eumini/api-client/react";
import { Button } from "@eumini/ui/button";
import { Callout } from "@eumini/ui/callout";
import { Input } from "@eumini/ui/input";
import { Label } from "@eumini/ui/label";
import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { handleFormError } from "../forms";

/** Recuperar a senha por código enviado ao e-mail, igual nos três apps. */
export function PasswordResetForm({ loginPath = "/entrar" }: { loginPath?: string }) {
  const api = useApiClient();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<"email" | "code" | "done">("email");

  const request = useMutation({
    mutationFn: async () =>
      unwrap(await api.POST("/api/auth/password/reset/", { body: { email } })),
    onSuccess: (data) => {
      toast.info(data.detail);
      setStep("code");
    },
    onError: (error) => handleFormError(error),
  });
  const confirm = useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST("/api/auth/password/reset/confirm/", {
          body: { email, code, new_password: password },
        }),
      ),
    onSuccess: () => setStep("done"),
    onError: (error) => handleFormError(error),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (step === "email") request.mutate();
    else confirm.mutate();
  }

  return (
    <div className="mx-auto max-w-md py-8">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Recuperar senha</h1>
      {step === "done" ? (
        <div className="mt-6 space-y-4">
          <Callout tone="accent" role="status" className="p-4">
            Senha redefinida. Por segurança, encerramos as sessões abertas.
          </Callout>
          <Button asChild variant="primary">
            <Link href={loginPath}>Entrar</Link>
          </Button>
        </div>
      ) : (
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email">E-mail</Label>
            <Input
              id="email"
              type="email"
              required
              autoComplete="email"
              disabled={step === "code"}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          {step === "code" && (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="code">Código enviado por e-mail</Label>
                <Input
                  id="code"
                  required
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={code}
                  onChange={(event) => setCode(event.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Nova senha</Label>
                <Input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>
            </>
          )}
          <Button
            type="submit"
            variant="primary"
            className="w-full"
            pending={request.isPending || confirm.isPending}
          >
            {step === "email" ? "Enviar código" : "Redefinir senha"}
          </Button>
        </form>
      )}
    </div>
  );
}
