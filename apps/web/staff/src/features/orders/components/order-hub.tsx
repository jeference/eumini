"use client";

import { ApiError } from "@eumini/api-client";
import { Button } from "@eumini/ui/button";
import { Callout } from "@eumini/ui/callout";
import { Card } from "@eumini/ui/card";
import { ConfirmDialog } from "@eumini/ui/confirm-dialog";
import { EmptyState } from "@eumini/ui/empty-state";
import { Input, Textarea } from "@eumini/ui/input";
import { Label } from "@eumini/ui/label";
import { categoryLabel } from "@eumini/ui/lib/categories";
import { formatBRL, formatCep, formatDate, formatDay } from "@eumini/ui/lib/format";
import { ORDER_STATUS } from "@eumini/ui/lib/status";
import { Skeleton } from "@eumini/ui/skeleton";
import { StatusBadge } from "@eumini/ui/status-badge";
import { handleFormError } from "@eumini/web-core/forms";
import { ArrowLeft, Download, FileBox, Image as ImageIcon, Upload, User } from "lucide-react";
import Link from "next/link";
import { type ReactNode, useId, useRef, useState } from "react";
import { toast } from "sonner";

import { usePartners } from "@/features/partners/hooks";

import {
  type StaffOrder,
  useOrder,
  useOrderActions,
  useOrderDownload,
  useOrderEvents,
} from "../hooks";
import { STAGES, eventLabel } from "../labels";

const SELECT =
  "h-11 w-full rounded-2xl border-2 border-stroke bg-surface px-3 text-base focus:border-accent focus:outline-none sm:text-sm";
const PRODUCTION_STATUSES = ["paid", "in_production"];

export function OrderHub({ id }: { id: string }) {
  const { data: order, error, isLoading } = useOrder(id);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-60 w-full" />
      </div>
    );
  }
  if (!order) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <EmptyState
        title={notFound ? "Pedido não encontrado" : "Não conseguimos abrir o pedido"}
        action={
          <Button asChild variant="primary">
            <Link href="/pedidos">Ver pedidos</Link>
          </Button>
        }
      />
    );
  }
  return <Hub order={order} />;
}

function Hub({ order }: { order: StaffOrder }) {
  const status = ORDER_STATUS[order.status];
  const stage = STAGES[order.stage];
  const inProduction = PRODUCTION_STATUSES.includes(order.status);

  return (
    <div className="space-y-5">
      <Link
        href="/pedidos"
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Pedidos
      </Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl font-semibold tracking-tight">{order.number}</h1>
        <StatusBadge label={status.label} tone={status.tone} />
        {order.stage !== "none" && <StatusBadge label={stage.label} tone={stage.tone} />}
        {inProduction && order.post_by && (
          <StatusBadge
            label={`${order.is_overdue ? "Atrasado, era" : "Postar até"} ${formatDay(order.post_by)}`}
            tone={order.is_overdue ? "danger" : "neutral"}
          />
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <Section title={`${order.piece_count} ${order.piece_count === 1 ? "peça" : "peças"}`}>
            {order.items.map((item, index) => (
              <ItemCard key={item.id} order={order} item={item} index={index} />
            ))}
          </Section>
          <Production order={order} />
          <Shipping order={order} />
          {order.photos.length > 0 && (
            <Section title="Fotos das peças prontas">
              <ul className="flex flex-wrap gap-2">
                {order.photos.map((photo) => (
                  <li key={photo.id}>
                    <a href={photo.url} target="_blank" rel="noopener noreferrer">
                      {/* eslint-disable-next-line @next/next/no-img-element -- URL assinada */}
                      <img
                        src={photo.url}
                        alt="Peças prontas"
                        className="size-28 rounded-xl bg-sunken object-cover"
                      />
                    </a>
                  </li>
                ))}
              </ul>
            </Section>
          )}
          <Issues order={order} />
          <History id={order.id} />
        </div>
        <aside className="space-y-5">
          <CustomerCard order={order} />
          <ChargesCard order={order} />
        </aside>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="font-display text-xl font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function ItemCard({
  order,
  item,
  index,
}: {
  order: StaffOrder;
  item: StaffOrder["items"][number];
  index: number;
}) {
  const download = useOrderDownload(order.id);
  const actions = useOrderActions(order.id);
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const open = item.job_status !== "shipped" && item.job_status !== "cancelled";
  const latest = item.files[0];

  function get(file: "image" | "photo" | "3mf") {
    download.mutate(
      { kind: "item", itemId: item.id, file },
      { onError: (error) => handleFormError(error) },
    );
  }

  function upload(file: File | undefined) {
    if (!file) return;
    actions.uploadFile.mutate(
      { itemId: item.id, file },
      {
        onSuccess: () => toast.success("3MF enviado."),
        onError: (error) => handleFormError(error),
        onSettled: () => {
          if (input.current) input.current.value = "";
        },
      },
    );
  }

  return (
    <Card className="space-y-4 p-4">
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="flex gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element -- URL assinada */}
          <img
            src={item.image_url}
            alt={`Imagem comprada do item ${index + 1}`}
            className="size-28 shrink-0 rounded-xl bg-sunken object-contain"
          />
          {item.photo_url && (
            // eslint-disable-next-line @next/next/no-img-element -- URL assinada
            <img
              src={item.photo_url}
              alt={`Foto enviada pelo cliente, item ${index + 1}`}
              className="size-28 shrink-0 rounded-xl bg-sunken object-cover"
            />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-1 text-sm">
          <p className="text-base font-semibold">
            Item {index + 1}: {categoryLabel(item.category)}, {item.size_label}
          </p>
          <p className="text-muted">
            {item.quantity} {item.quantity === 1 ? "unidade" : "unidades"} de{" "}
            {formatBRL(item.unit_price_cents)}, maior lado {Math.round(item.longest_side_mm / 10)}{" "}
            cm
          </p>
          {item.payout_cents !== null && (
            <p className="text-muted">Ganho do parceiro: {formatBRL(item.payout_cents)}</p>
          )}
          {item.customer_text && (
            <p>
              <span className="text-muted">Pedido do cliente:</span> {item.customer_text}
            </p>
          )}
          {item.prompt_text && (
            <details>
              <summary className="cursor-pointer text-muted">Prompt enviado à IA</summary>
              <p className="mt-1 whitespace-pre-line rounded-xl bg-sunken p-3 text-xs">
                {item.prompt_text}
              </p>
            </details>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" size="sm" onClick={() => get("image")}>
          <ImageIcon aria-hidden />
          Imagem
        </Button>
        <Button variant="secondary" size="sm" onClick={() => get("photo")}>
          <User aria-hidden />
          Foto do cliente
        </Button>
        <Button variant="secondary" size="sm" disabled={!latest} onClick={() => get("3mf")}>
          <FileBox aria-hidden />
          3MF
        </Button>
        {open && (
          <>
            <input
              ref={input}
              id={inputId}
              type="file"
              accept=".3mf"
              className="sr-only"
              onChange={(event) => upload(event.target.files?.[0])}
            />
            <Button
              asChild
              variant={latest ? "secondary" : "primary"}
              size="sm"
              pending={actions.uploadFile.isPending}
            >
              <label htmlFor={inputId} className="cursor-pointer">
                <Upload aria-hidden />
                {latest ? "Enviar nova versão" : "Enviar 3MF"}
              </label>
            </Button>
          </>
        )}
      </div>
      <p className="text-xs text-muted">
        {latest
          ? `3MF versão ${latest.version}, de ${formatDate(latest.uploaded_at)}, ${(latest.size_bytes / 1_000_000).toFixed(1)} MB`
          : "Sem 3MF. O parceiro só começa a imprimir depois do arquivo."}
      </p>
    </Card>
  );
}

function Production({ order }: { order: StaffOrder }) {
  const partners = usePartners();
  const actions = useOrderActions(order.id);
  const [partnerId, setPartnerId] = useState("");
  const [confirming, setConfirming] = useState<"assign" | "unassign" | null>(null);
  const [reason, setReason] = useState("");
  const canChange = [
    "unassigned",
    "assigned",
    "in_production",
    "awaiting_label",
    "to_post",
  ].includes(order.stage);
  const hasPartner = order.stage !== "unassigned" && order.partner !== null;
  const active = partners.data?.results.filter(
    (partner) => partner.status === "active" && partner.id !== order.partner?.id,
  );
  const payout = order.items.reduce((sum, item) => sum + (item.payout_cents ?? 0), 0);

  function close() {
    setConfirming(null);
    setReason("");
  }

  function assign() {
    actions.assign.mutate(
      { partnerId, reason },
      {
        onSuccess: () => {
          toast.success("Pedido atribuído. O parceiro recebeu um e-mail.");
          setPartnerId("");
          close();
        },
        onError: (error) => handleFormError(error),
      },
    );
  }

  function unassign() {
    if (!reason.trim()) {
      toast.error("Conte o motivo.");
      return;
    }
    actions.unassign.mutate(reason.trim(), {
      onSuccess: () => {
        toast.success("Pedido retirado do parceiro.");
        close();
      },
      onError: (error) => handleFormError(error),
    });
  }

  return (
    <Section title="Produção">
      <Card className="space-y-4 p-4">
        {hasPartner ? (
          <div className="space-y-1 text-sm">
            <p>
              Com{" "}
              <Link
                href={`/parceiros/${order.partner?.id}`}
                className="font-semibold text-accent underline"
              >
                {order.partner?.name}
              </Link>
              {order.assigned_at && `, desde ${formatDate(order.assigned_at)}`}
            </p>
            {payout > 0 && <p className="text-muted">Ganho combinado: {formatBRL(payout)}</p>}
          </div>
        ) : (
          <p className="text-sm text-muted">
            {order.stage === "none"
              ? "Este pedido não tem produção: ainda não foi pago."
              : "Sem parceiro."}
          </p>
        )}

        {canChange && (
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-1.5">
              <Label htmlFor="partner">{hasPartner ? "Passar para" : "Atribuir a"}</Label>
              <select
                id="partner"
                className={SELECT}
                value={partnerId}
                onChange={(event) => setPartnerId(event.target.value)}
              >
                <option value="">Escolha o parceiro</option>
                {active?.map((partner) => (
                  <option key={partner.id} value={partner.id}>
                    {partner.name} ({partner.active_orders} ativos)
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="primary"
              disabled={!partnerId}
              pending={actions.assign.isPending && confirming === null}
              onClick={() => (hasPartner ? setConfirming("assign") : assign())}
            >
              {hasPartner ? "Reatribuir" : "Atribuir"}
            </Button>
            {hasPartner && (
              <Button variant="danger" onClick={() => setConfirming("unassign")}>
                Retirar
              </Button>
            )}
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={confirming !== null}
        onOpenChange={(next) => !next && close()}
        title={confirming === "assign" ? "Passar para outro parceiro?" : "Retirar do parceiro?"}
        description={
          `${order.partner?.name ?? "O parceiro"} recebe um e-mail para não imprimir nem postar. ` +
          "A etiqueta ainda não postada é descartada: cancele-a no Melhor Envio."
        }
        confirmLabel={confirming === "assign" ? "Reatribuir" : "Retirar"}
        tone="danger"
        pending={actions.assign.isPending || actions.unassign.isPending}
        onConfirm={() => (confirming === "assign" ? assign() : unassign())}
      >
        <Label htmlFor="reason">Motivo</Label>
        <Textarea
          id="reason"
          className="mt-1.5"
          rows={3}
          maxLength={500}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
        />
      </ConfirmDialog>
    </Section>
  );
}

function Shipping({ order }: { order: StaffOrder }) {
  const actions = useOrderActions(order.id);
  const download = useOrderDownload(order.id);
  const [pdf, setPdf] = useState<File | null>(null);
  const [carrier, setCarrier] = useState("");
  const [tracking, setTracking] = useState("");
  const [delivering, setDelivering] = useState(false);
  const shipment = order.shipment;
  const canAttach = order.stage === "awaiting_label" || order.stage === "to_post";

  if (!shipment && !canAttach) return null;

  function attach() {
    if (!pdf || !carrier.trim() || !tracking.trim()) {
      toast.error("Envie o PDF e informe a transportadora e o rastreio.");
      return;
    }
    actions.attachLabel.mutate(
      { pdf, carrier: carrier.trim(), trackingCode: tracking.trim() },
      {
        onSuccess: () => {
          setPdf(null);
          setCarrier("");
          setTracking("");
          toast.success("Etiqueta anexada. O parceiro recebeu um e-mail.");
        },
        onError: (error) => handleFormError(error),
      },
    );
  }

  return (
    <Section title="Envio">
      <Card className="space-y-4 p-4">
        {shipment && (
          <div className="flex flex-col gap-3 text-sm sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p>
                {shipment.carrier}, rastreio{" "}
                <span className="font-mono font-semibold">{shipment.tracking_code}</span>
              </p>
              <p className="text-muted">
                {shipment.delivered_at
                  ? `Entregue em ${formatDate(shipment.delivered_at)}`
                  : shipment.shipped_at
                    ? `Postado em ${formatDate(shipment.shipped_at)}`
                    : "Etiqueta anexada, ainda não postada"}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {shipment.has_label && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    download.mutate(
                      { kind: "label" },
                      { onError: (error) => handleFormError(error) },
                    )
                  }
                >
                  <Download aria-hidden />
                  Etiqueta
                </Button>
              )}
              {order.status === "shipped" && (
                <Button variant="primary" size="sm" onClick={() => setDelivering(true)}>
                  Marcar entregue
                </Button>
              )}
            </div>
          </div>
        )}

        {canAttach && (
          <div className="space-y-3">
            <p className="text-sm text-muted">
              Compre a etiqueta no Melhor Envio com origem no CEP do parceiro e anexe aqui.
              {order.stage === "to_post" && " Uma nova etiqueta substitui a atual."}
            </p>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="label-pdf">PDF da etiqueta</Label>
                <Input
                  id="label-pdf"
                  type="file"
                  accept="application/pdf"
                  className="pt-2.5"
                  onChange={(event) => setPdf(event.target.files?.[0] ?? null)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="carrier">Transportadora</Label>
                <Input
                  id="carrier"
                  placeholder="Correios PAC"
                  value={carrier}
                  onChange={(event) => setCarrier(event.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="tracking">Rastreio</Label>
                <Input
                  id="tracking"
                  value={tracking}
                  onChange={(event) => setTracking(event.target.value.toUpperCase())}
                />
              </div>
            </div>
            <Button variant="primary" pending={actions.attachLabel.isPending} onClick={attach}>
              {order.stage === "to_post" ? "Substituir etiqueta" : "Anexar etiqueta"}
            </Button>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={delivering}
        onOpenChange={setDelivering}
        title="Marcar como entregue?"
        description="Confira no rastreio. O cliente recebe um e-mail de pedido entregue."
        confirmLabel="Marcar entregue"
        pending={actions.deliver.isPending}
        onConfirm={() =>
          actions.deliver.mutate(undefined, {
            onSuccess: () => {
              setDelivering(false);
              toast.success("Pedido entregue.");
            },
            onError: (error) => handleFormError(error),
          })
        }
      />
    </Section>
  );
}

function Issues({ order }: { order: StaffOrder }) {
  const actions = useOrderActions(order.id);
  const [resolving, setResolving] = useState<string | null>(null);
  const [note, setNote] = useState("");
  if (order.issues.length === 0) return null;

  return (
    <Section title="Problemas reportados">
      {order.issues.map((issue) => (
        <Card key={issue.id} className="space-y-2 p-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">{issue.partner.name}</span>
            <span className="text-muted">{formatDate(issue.created_at)}</span>
            <StatusBadge
              label={issue.resolved_at ? "Resolvido" : "Em aberto"}
              tone={issue.resolved_at ? "success" : "danger"}
            />
          </div>
          <p className="whitespace-pre-line">{issue.text}</p>
          {issue.photo_url && (
            <a href={issue.photo_url} target="_blank" rel="noopener noreferrer">
              {/* eslint-disable-next-line @next/next/no-img-element -- URL assinada */}
              <img src={issue.photo_url} alt="" className="size-24 rounded-xl object-cover" />
            </a>
          )}
          {issue.resolution_note && <p className="text-muted">Resposta: {issue.resolution_note}</p>}
          {!issue.resolved_at && (
            <Button variant="secondary" size="sm" onClick={() => setResolving(issue.id)}>
              Resolver
            </Button>
          )}
        </Card>
      ))}
      <ConfirmDialog
        open={resolving !== null}
        onOpenChange={(next) => !next && setResolving(null)}
        title="Resolver problema"
        description="O parceiro vê esta resposta no pedido."
        confirmLabel="Resolver"
        pending={actions.resolveIssue.isPending}
        onConfirm={() => {
          if (!resolving || !note.trim()) {
            toast.error("Conte como foi resolvido.");
            return;
          }
          actions.resolveIssue.mutate(
            { issueId: resolving, note: note.trim() },
            {
              onSuccess: () => {
                setResolving(null);
                setNote("");
              },
              onError: (error) => handleFormError(error),
            },
          );
        }}
      >
        <Label htmlFor="note">Resposta</Label>
        <Textarea
          id="note"
          className="mt-1.5"
          rows={3}
          maxLength={1000}
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
      </ConfirmDialog>
    </Section>
  );
}

function CustomerCard({ order }: { order: StaffOrder }) {
  return (
    <Card className="space-y-3 p-4 text-sm">
      <h2 className="font-display text-lg font-semibold">Cliente e entrega</h2>
      <div>
        <p className="font-semibold">{order.customer_name}</p>
        <p className="break-all text-muted">{order.customer_email}</p>
        <p className="text-muted">CPF {order.cpf_masked}</p>
      </div>
      <div className="text-muted">
        <p>
          {order.street}, {order.address_number}
          {order.complement && `, ${order.complement}`}
        </p>
        <p>
          {order.neighborhood}, {order.city}/{order.state}
        </p>
        <p>CEP {formatCep(order.postal_code)}</p>
      </div>
      <div className="text-muted">
        <p>
          {order.shipping_service_name}
          {order.shipping_company && ` (${order.shipping_company})`}, {order.delivery_days} dias
          prometidos
        </p>
      </div>
      <dl className="space-y-1 border-t border-line pt-3">
        <Row label="Produtos" value={formatBRL(order.subtotal_cents)} />
        <Row label="Frete" value={formatBRL(order.shipping_cents)} />
        <Row label="Total" value={formatBRL(order.total_cents)} strong />
      </dl>
    </Card>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex justify-between">
      <dt className="text-muted">{label}</dt>
      <dd className={strong ? "font-semibold tabular-nums" : "tabular-nums"}>{value}</dd>
    </div>
  );
}

const CHARGE_STATUS: Record<string, string> = {
  pending: "Pendente",
  paid: "Paga",
  expired: "Expirada",
  failed: "Falhou",
  refunded: "Reembolsada",
};

function ChargesCard({ order }: { order: StaffOrder }) {
  if (order.charges.length === 0) return null;
  return (
    <Card className="space-y-2 p-4 text-sm">
      <h2 className="font-display text-lg font-semibold">Cobranças</h2>
      {order.charges.map((charge) => (
        <div key={charge.id} className="flex justify-between gap-2">
          <span>
            {charge.method === "PIX"
              ? "Pix"
              : `Cartão ${charge.card_brand} •••• ${charge.card_last_four}`}
            <span className="block text-xs text-muted">
              {CHARGE_STATUS[charge.status] ?? charge.status}
              {charge.paid_at && `, ${formatDate(charge.paid_at)}`}
              {charge.disputed_at && ", em disputa"}
            </span>
          </span>
          <span className="tabular-nums">{formatBRL(charge.amount_cents)}</span>
        </div>
      ))}
      <Callout tone="neutral" className="text-xs">
        Reembolso: pelo painel do gateway. O pedido se atualiza sozinho.
      </Callout>
    </Card>
  );
}

/** O motivo de recusa ou retirada, quando o evento traz um. */
function reasonOf(payload: unknown): string {
  if (payload && typeof payload === "object" && "reason" in payload) {
    const reason = (payload as { reason: unknown }).reason;
    return typeof reason === "string" ? reason : "";
  }
  return "";
}

function History({ id }: { id: string }) {
  const { data } = useOrderEvents(id);
  if (!data) return null;
  return (
    <Section title="Histórico">
      <ol className="space-y-2 border-l-2 border-line pl-4 text-sm">
        {data.map((event) => {
          const reason = reasonOf(event.payload);
          return (
            <li key={event.id}>
              <span className="font-semibold">{eventLabel(event.event, event.aggregate)}</span>{" "}
              <span className="text-muted">
                {formatDate(event.created_at)}, {event.actor}
              </span>
              {reason && <span className="block text-muted">Motivo: {reason}</span>}
            </li>
          );
        })}
      </ol>
    </Section>
  );
}
