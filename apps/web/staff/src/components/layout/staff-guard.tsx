"use client";

import { Button } from "@eumini/ui/button";
import { EmptyState } from "@eumini/ui/empty-state";
import { signOutAndRedirect } from "@eumini/web-core/auth-client";
import { AuthGuard } from "@eumini/web-core/components/auth-guard";
import { useSession } from "@eumini/web-core/session";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const STAFF_ROLES = ["staff", "admin"];

function RoleCheck({ children }: { children: ReactNode }) {
  const roles = useSession((state) => state.user?.roles ?? []);
  if (!roles.some((role) => STAFF_ROLES.includes(role))) {
    return (
      <div className="mx-auto max-w-md px-4 py-16">
        <EmptyState
          title="Esta conta não é da equipe"
          description="O app Staff é só para quem trabalha na EuMini."
          action={
            <Button variant="primary" onClick={() => void signOutAndRedirect("/entrar")}>
              Sair e entrar com outra conta
            </Button>
          }
        />
      </div>
    );
  }
  return <>{children}</>;
}

/** Conta autenticada com o papel da equipe. Quem decide de verdade é o backend. */
export function StaffGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  return (
    <AuthGuard loginPath={`/entrar?next=${encodeURIComponent(pathname)}`}>
      <RoleCheck>{children}</RoleCheck>
    </AuthGuard>
  );
}
