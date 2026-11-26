"use client";

import { ApiError } from "@eumini/api-client";
import { Button } from "@eumini/ui/button";
import { EmptyState } from "@eumini/ui/empty-state";
import { Skeleton } from "@eumini/ui/skeleton";
import { signOutAndRedirect } from "@eumini/web-core/auth-client";
import { AuthGuard } from "@eumini/web-core/components/auth-guard";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { usePartnerMe } from "@/features/account/hooks";

function PartnerCheck({ children }: { children: ReactNode }) {
  const { data, error, isLoading } = usePartnerMe();

  if (error instanceof ApiError && error.status === 403) {
    return (
      <div className="mx-auto max-w-md px-4 py-16">
        <EmptyState
          title="Esta conta não é de parceiro"
          description="O app de parceiros é só para quem imprime para a EuMini. Se você recebeu um convite, entre com o e-mail dele."
          action={
            <Button variant="primary" onClick={() => void signOutAndRedirect("/entrar")}>
              Sair e entrar com outra conta
            </Button>
          }
        />
      </div>
    );
  }
  if (isLoading || !data) {
    return (
      <div className="mx-auto w-full max-w-5xl space-y-3 px-4 py-8">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    );
  }
  return <>{children}</>;
}

/** Conta autenticada e ligada a um parceiro ativo. Quem decide de verdade é o backend. */
export function PartnerGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <AuthGuard loginPath={`/entrar?next=${encodeURIComponent(pathname)}`}>
      <PartnerCheck>{children}</PartnerCheck>
    </AuthGuard>
  );
}
