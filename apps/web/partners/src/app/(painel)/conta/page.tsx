"use client";

import { Button } from "@eumini/ui/button";
import { Card } from "@eumini/ui/card";
import { formatCep } from "@eumini/ui/lib/format";
import { useLogout } from "@eumini/web-core/auth-client";
import { useSession } from "@eumini/web-core/session";

import { usePartnerMe } from "@/features/account/hooks";

const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL ?? "";

export default function AccountPage() {
  const { data: partner } = usePartnerMe();
  const email = useSession((state) => state.user?.email);
  const logout = useLogout();

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Conta</h1>
      <Card className="divide-y divide-line">
        <Row label="Parceiro" value={partner?.name} />
        <Row label="E-mail de acesso" value={email} />
        <Row
          label="CEP de origem dos envios"
          value={partner ? formatCep(partner.origin_postal_code) : undefined}
        />
        <Row
          label="Chave PIX para os repasses"
          value={partner?.pix_key_masked || "Não cadastrada"}
        />
      </Card>
      <p className="text-sm text-muted">
        Para mudar o CEP ou a chave PIX, fale com a EuMini
        {SUPPORT_EMAIL ? (
          <>
            {" "}
            em{" "}
            <a href={`mailto:${SUPPORT_EMAIL}`} className="text-accent underline">
              {SUPPORT_EMAIL}
            </a>
          </>
        ) : null}
        .
      </p>
      <Button
        variant="secondary"
        pending={logout.isPending}
        onClick={() => logout.mutate("/entrar")}
      >
        Sair
      </Button>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex flex-col gap-0.5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-sm text-muted">{label}</span>
      <span className="font-semibold">{value ?? "…"}</span>
    </div>
  );
}
