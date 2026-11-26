"use client";

import { Button } from "@eumini/ui/button";
import { EmptyState } from "@eumini/ui/empty-state";
import { formatBRL } from "@eumini/ui/lib/format";
import { Skeleton } from "@eumini/ui/skeleton";
import { StatusBadge } from "@eumini/ui/status-badge";
import { ChevronRight, Plus } from "lucide-react";
import Link from "next/link";

import { usePartners } from "@/features/partners/hooks";

export default function PartnersPage() {
  const { data, isLoading } = usePartners();

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-3xl font-semibold tracking-tight">Parceiros</h1>
        <Button asChild variant="primary">
          <Link href="/parceiros/novo">
            <Plus aria-hidden />
            Novo parceiro
          </Link>
        </Button>
      </div>
      {isLoading && <Skeleton className="h-20 w-full" />}
      {data && data.results.length === 0 && (
        <EmptyState
          title="Nenhum parceiro ainda"
          description="Cadastre quem vai imprimir. Ele recebe um convite por e-mail para criar a senha."
        />
      )}
      <ul className="space-y-3">
        {data?.results.map((partner) => (
          <li key={partner.id}>
            <Link
              href={`/parceiros/${partner.id}`}
              className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-4 shadow-card transition-colors hover:border-accent"
            >
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold">{partner.name}</span>
                  {partner.status === "inactive" && <StatusBadge label="Inativo" tone="neutral" />}
                  {partner.is_internal && <StatusBadge label="EuMini" tone="progress" />}
                  {!partner.invite_accepted && partner.login_email && (
                    <StatusBadge label="Convite pendente" tone="neutral" />
                  )}
                </span>
                <span className="block truncate text-sm text-muted">
                  {partner.login_email || "Sem login"}
                </span>
              </span>
              <span className="hidden text-right text-sm sm:block">
                <span className="block">
                  {partner.active_orders} {partner.active_orders === 1 ? "ativo" : "ativos"}
                  {partner.overdue_orders > 0 && (
                    <span className="font-semibold text-danger">
                      , {partner.overdue_orders} atrasado{partner.overdue_orders === 1 ? "" : "s"}
                    </span>
                  )}
                </span>
                <span className="block text-muted">
                  A pagar {formatBRL(partner.to_receive_cents)}
                </span>
              </span>
              <ChevronRight className="size-5 shrink-0 text-muted" aria-hidden />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
