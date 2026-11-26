"use client";

import { Button } from "@eumini/ui/button";
import { Callout } from "@eumini/ui/callout";
import { Card } from "@eumini/ui/card";
import { Checkbox } from "@eumini/ui/checkbox";
import { ConfirmDialog } from "@eumini/ui/confirm-dialog";
import { EmptyState } from "@eumini/ui/empty-state";
import { Input } from "@eumini/ui/input";
import { Label } from "@eumini/ui/label";
import { categoryLabel } from "@eumini/ui/lib/categories";
import { formatBRL, formatCep, formatDate, formatDay } from "@eumini/ui/lib/format";
import { Skeleton } from "@eumini/ui/skeleton";
import { StatusBadge } from "@eumini/ui/status-badge";
import { handleFormError } from "@eumini/web-core/forms";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import {
  type PartnerEntry,
  type StaffPartner,
  usePartner,
  usePartnerActions,
  usePartnerEntries,
  usePartnerPayouts,
} from "../hooks";
import { parseBRL, selectedTotal } from "../money";

export function PartnerDetail({ id }: { id: string }) {
  const { data: partner, isLoading } = usePartner(id);
  if (isLoading) return <Skeleton className="h-60 w-full" />;
  if (!partner) {
    return (
      <EmptyState
        title="Parceiro não encontrado"
        action={
          <Button asChild variant="primary">
            <Link href="/parceiros">Ver parceiros</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <Link
        href="/parceiros"
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Parceiros
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl font-semibold tracking-tight">{partner.name}</h1>
        <StatusBadge
          label={partner.status === "active" ? "Ativo" : "Inativo"}
          tone={partner.status === "active" ? "success" : "neutral"}
        />
        {!partner.invite_accepted && partner.login_email && (
          <StatusBadge label="Convite pendente" tone="neutral" />
        )}
      </div>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <Statement partner={partner} />
          <Payouts id={partner.id} />
        </div>
        <aside className="space-y-5">
          <Profile partner={partner} />
          <Adjustment id={partner.id} />
        </aside>
      </div>
    </div>
  );
}

function Profile({ partner }: { partner: StaffPartner }) {
  const actions = usePartnerActions(partner.id);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(partner.name);
  const [cep, setCep] = useState(formatCep(partner.origin_postal_code));
  const [pix, setPix] = useState(partner.pix_key);
  const [toggling, setToggling] = useState(false);
  const active = partner.status === "active";

  function save(event: FormEvent) {
    event.preventDefault();
    actions.update.mutate(
      { name, origin_postal_code: cep, pix_key: pix },
      {
        onSuccess: () => {
          setEditing(false);
          toast.success("Dados salvos.");
        },
        onError: (error) => handleFormError(error),
      },
    );
  }

  return (
    <Card className="space-y-4 p-4 text-sm">
      <h2 className="font-display text-lg font-semibold">Dados</h2>
      {editing ? (
        <form onSubmit={save} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="p-name">Nome</Label>
            <Input id="p-name" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-cep">CEP de origem</Label>
            <Input
              id="p-cep"
              inputMode="numeric"
              value={cep}
              onChange={(event) => setCep(formatCep(event.target.value))}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="p-pix">Chave PIX</Label>
            <Input id="p-pix" value={pix} onChange={(event) => setPix(event.target.value)} />
          </div>
          <div className="flex gap-2">
            <Button type="submit" variant="primary" size="sm" pending={actions.update.isPending}>
              Salvar
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setEditing(false)}>
              Cancelar
            </Button>
          </div>
        </form>
      ) : (
        <dl className="space-y-2">
          <Field label="Login" value={partner.login_email || "Sem login"} />
          <Field label="CEP de origem" value={formatCep(partner.origin_postal_code)} />
          <Field label="Chave PIX" value={partner.pix_key || "Não cadastrada"} />
          <Field
            label="Pedidos ativos"
            value={`${partner.active_orders}${partner.overdue_orders ? `, ${partner.overdue_orders} atrasados` : ""}`}
          />
          <Field label="Desde" value={formatDate(partner.created_at)} />
        </dl>
      )}
      {!editing && (
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
            Editar
          </Button>
          {!partner.invite_accepted && partner.login_email && (
            <Button
              variant="secondary"
              size="sm"
              pending={actions.invite.isPending}
              onClick={() =>
                actions.invite.mutate(undefined, {
                  onSuccess: () => toast.success("Convite reenviado."),
                  onError: (error) => handleFormError(error),
                })
              }
            >
              Reenviar convite
            </Button>
          )}
          <Button
            variant={active ? "danger" : "secondary"}
            size="sm"
            onClick={() => setToggling(true)}
          >
            {active ? "Desativar" : "Reativar"}
          </Button>
        </div>
      )}
      <ConfirmDialog
        open={toggling}
        onOpenChange={setToggling}
        title={active ? "Desativar o parceiro?" : "Reativar o parceiro?"}
        description={
          active
            ? "Ele perde o acesso na hora e não recebe novos pedidos. Só é possível sem pedidos ativos."
            : "Ele volta a entrar no app e a receber pedidos."
        }
        confirmLabel={active ? "Desativar" : "Reativar"}
        tone={active ? "danger" : "primary"}
        pending={actions.deactivate.isPending || actions.reactivate.isPending}
        onConfirm={() =>
          (active ? actions.deactivate : actions.reactivate).mutate(undefined, {
            onSuccess: () => setToggling(false),
            onError: (error) => {
              setToggling(false);
              handleFormError(error);
            },
          })
        }
      />
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className="break-all font-semibold">{value}</dd>
    </div>
  );
}

function entryTitle(entry: PartnerEntry): string {
  if (entry.kind === "adjustment") return `Ajuste: ${entry.note}`;
  return `Pedido ${entry.order_number}, ${categoryLabel(entry.category)} ${entry.size_label}, ${entry.quantity} un.`;
}

function today(): string {
  return new Date().toLocaleDateString("sv-SE", { timeZone: "America/Sao_Paulo" });
}

function Statement({ partner }: { partner: StaffPartner }) {
  const { data, isLoading } = usePartnerEntries(partner.id, true);
  const actions = usePartnerActions(partner.id);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [paidOn, setPaidOn] = useState(today);
  const [note, setNote] = useState("");
  const [receipt, setReceipt] = useState<File | null>(null);
  const [confirming, setConfirming] = useState(false);
  const entries = data?.results ?? [];
  const total = selectedTotal(entries, selected);

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function pay() {
    actions.payout.mutate(
      { entryIds: [...selected], paidOn, amountCents: total, note, receipt },
      {
        onSuccess: () => {
          setSelected(new Set());
          setNote("");
          setReceipt(null);
          setConfirming(false);
          toast.success("Repasse registrado. O parceiro recebeu um e-mail.");
        },
        onError: (error) => {
          setConfirming(false);
          handleFormError(error);
        },
      },
    );
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-xl font-semibold">A pagar</h2>
        <span className="font-semibold tabular-nums">{formatBRL(partner.to_receive_cents)}</span>
      </div>
      {isLoading && <Skeleton className="h-24 w-full" />}
      {data && entries.length === 0 && (
        <p className="rounded-2xl bg-sunken px-4 py-6 text-center text-sm text-muted">
          Nada em aberto. Os ganhos entram quando o parceiro posta.
        </p>
      )}
      {entries.length > 0 && (
        <>
          <div className="flex justify-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() =>
                setSelected(
                  selected.size === entries.length
                    ? new Set()
                    : new Set(entries.map((entry) => entry.id)),
                )
              }
            >
              {selected.size === entries.length ? "Desmarcar tudo" : "Marcar tudo"}
            </Button>
          </div>
          <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
            {entries.map((entry) => (
              <li key={entry.id}>
                <Checkbox
                  checked={selected.has(entry.id)}
                  onChange={() => toggle(entry.id)}
                  className="w-full items-center px-4 py-3 text-sm [&>span:last-child]:flex-1"
                >
                  <span className="flex items-center gap-3">
                    <span className="min-w-0 flex-1">
                      <span className="block font-semibold">{entryTitle(entry)}</span>
                      <span className="text-muted">{formatDate(entry.created_at)}</span>
                    </span>
                    <span
                      className={`font-semibold tabular-nums ${entry.amount_cents < 0 ? "text-danger" : ""}`}
                    >
                      {formatBRL(entry.amount_cents)}
                    </span>
                  </span>
                </Checkbox>
              </li>
            ))}
          </ul>
          <Card className="space-y-3 p-4">
            <p className="text-sm">
              {selected.size} {selected.size === 1 ? "lançamento" : "lançamentos"} escolhidos:{" "}
              <strong className="tabular-nums">{formatBRL(total)}</strong>
            </p>
            {!partner.pix_key && (
              <Callout tone="danger">Cadastre a chave PIX do parceiro antes de pagar.</Callout>
            )}
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="paid-on">Data do PIX</Label>
                <Input
                  id="paid-on"
                  type="date"
                  value={paidOn}
                  onChange={(event) => setPaidOn(event.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="receipt">Comprovante (opcional)</Label>
                <Input
                  id="receipt"
                  type="file"
                  accept="application/pdf,image/*"
                  className="pt-2.5"
                  onChange={(event) => setReceipt(event.target.files?.[0] ?? null)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="payout-note">Nota (opcional)</Label>
                <Input
                  id="payout-note"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
              </div>
            </div>
            <Button
              variant="primary"
              disabled={selected.size === 0 || total <= 0 || !partner.pix_key}
              onClick={() => setConfirming(true)}
            >
              Registrar repasse de {formatBRL(total)}
            </Button>
          </Card>
        </>
      )}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={`Registrar repasse de ${formatBRL(total)}?`}
        description={`Confirme só depois de fazer o PIX para ${partner.pix_key}. Repasse registrado não pode ser editado: um erro se corrige com ajuste.`}
        confirmLabel="Registrar"
        pending={actions.payout.isPending}
        onConfirm={pay}
      />
    </section>
  );
}

function Adjustment({ id }: { id: string }) {
  const actions = usePartnerActions(id);
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    const cents = parseBRL(value);
    if (cents === null || cents === 0) {
      toast.error("Informe um valor, como 25,00 ou -25,00.");
      return;
    }
    actions.adjustment.mutate(
      { amountCents: cents, note },
      {
        onSuccess: () => {
          setValue("");
          setNote("");
          toast.success("Ajuste lançado.");
        },
        onError: (error) => handleFormError(error),
      },
    );
  }

  return (
    <Card className="p-4">
      <form onSubmit={submit} className="space-y-3 text-sm">
        <h2 className="font-display text-lg font-semibold">Ajuste</h2>
        <p className="text-muted">Crédito ou débito no extrato. Use negativo para descontar.</p>
        <div className="space-y-1.5">
          <Label htmlFor="adj-value">Valor em reais</Label>
          <Input
            id="adj-value"
            inputMode="decimal"
            placeholder="-25,00"
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="adj-note">Motivo</Label>
          <Input id="adj-note" value={note} onChange={(event) => setNote(event.target.value)} />
        </div>
        <Button type="submit" variant="secondary" pending={actions.adjustment.isPending}>
          Lançar ajuste
        </Button>
      </form>
    </Card>
  );
}

function Payouts({ id }: { id: string }) {
  const { data } = usePartnerPayouts(id);
  if (!data || data.results.length === 0) return null;
  return (
    <section className="space-y-3">
      <h2 className="font-display text-xl font-semibold">Repasses feitos</h2>
      <ul className="divide-y divide-line overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
        {data.results.map((payout) => (
          <li key={payout.id} className="flex items-center gap-3 px-4 py-3 text-sm">
            <span className="min-w-0 flex-1">
              <span className="block font-semibold">PIX em {formatDay(payout.paid_on)}</span>
              <span className="text-muted">
                {payout.entry_count} {payout.entry_count === 1 ? "lançamento" : "lançamentos"}
                {payout.note && `, ${payout.note}`}
              </span>
            </span>
            {payout.receipt_url && (
              <a
                href={payout.receipt_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent underline"
              >
                Comprovante
              </a>
            )}
            <span className="font-semibold tabular-nums">{formatBRL(payout.amount_cents)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
