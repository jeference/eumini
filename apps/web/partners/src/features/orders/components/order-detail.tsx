"use client";

import { ApiError } from "@eumini/api-client";
import { Button } from "@eumini/ui/button";
import { Callout } from "@eumini/ui/callout";
import { Card } from "@eumini/ui/card";
import { ConfirmDialog } from "@eumini/ui/confirm-dialog";
import { EmptyState } from "@eumini/ui/empty-state";
import { Textarea } from "@eumini/ui/input";
import { Label } from "@eumini/ui/label";
import { formatDate } from "@eumini/ui/lib/format";
import { Skeleton } from "@eumini/ui/skeleton";
import { StatusBadge } from "@eumini/ui/status-badge";
import { handleFormError } from "@eumini/web-core/forms";
import { ArrowLeft, Download, FileBox, Image as ImageIcon, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { categoryLabel } from "@eumini/ui/lib/categories";

import { GROUPS } from "../groups";
import { type PartnerOrder, useDownload, useOrder, useOrderActions } from "../hooks";
import { DeadlineBadge } from "./deadline-badge";
import { PhotoPicker } from "./photo-picker";

const READY_PHOTOS_MAX = 5;

export function OrderDetail({ id }: { id: string }) {
  const { data: order, error, isLoading } = useOrder(id);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (!order) {
    const notFound = error instanceof ApiError && error.status === 404;
    return (
      <EmptyState
        title={notFound ? "Pedido não encontrado" : "Não conseguimos abrir o pedido"}
        description={
          notFound
            ? "Ele pode ter sido recusado por você ou passado para outro parceiro."
            : "Tente de novo em instantes."
        }
        action={
          <Button asChild variant="primary">
            <Link href="/impressoes">Ver impressões</Link>
          </Button>
        }
      />
    );
  }
  return <OrderHub order={order} />;
}

function OrderHub({ order }: { order: PartnerOrder }) {
  const group = GROUPS[order.group];
  const cancelled = order.group === "cancelled";
  const active = !cancelled && order.group !== "posted";
  const fileUpdated = order.items.some((item) => (item.production_file?.version ?? 0) > 1);

  return (
    <div className="space-y-5">
      <Link
        href={`/impressoes?aba=${order.group}`}
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
      >
        <ArrowLeft className="size-4" aria-hidden />
        Impressões
      </Link>

      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl font-semibold tracking-tight">{order.number}</h1>
        <StatusBadge label={group.label} tone={group.tone} />
        {active && <DeadlineBadge order={order} />}
      </div>

      <Callout tone={cancelled ? "danger" : "accent"} role="status" className="p-4">
        {cancelled && <strong className="block">Cancelado: não imprima nem poste.</strong>}
        {!cancelled && group.nextStep}
      </Callout>

      {fileUpdated && active && (
        <Callout tone="neutral" role="status">
          A EuMini enviou um arquivo novo para um dos itens. Baixe de novo antes de imprimir.
        </Callout>
      )}

      <section aria-labelledby="itens" className="space-y-3">
        <h2 id="itens" className="font-display text-xl font-semibold">
          {order.piece_count} {order.piece_count === 1 ? "peça" : "peças"}
        </h2>
        {order.items.map((item, index) => (
          <ItemCard key={item.id} order={order} item={item} index={index} disabled={cancelled} />
        ))}
      </section>

      <NextAction order={order} />

      {order.label && <LabelCard order={order} />}

      {order.photos.length > 0 && (
        <section aria-labelledby="fotos" className="space-y-2">
          <h2 id="fotos" className="font-display text-xl font-semibold">
            Fotos das peças prontas
          </h2>
          <ul className="flex flex-wrap gap-2">
            {order.photos.map((photo) => (
              <li key={photo.id}>
                {/* eslint-disable-next-line @next/next/no-img-element -- imagem por URL assinada */}
                <img src={photo.url} alt="" className="size-24 rounded-xl bg-sunken object-cover" />
              </li>
            ))}
          </ul>
        </section>
      )}

      <Issues order={order} canReport={active} />
    </div>
  );
}

function ItemCard({
  order,
  item,
  index,
  disabled,
}: {
  order: PartnerOrder;
  item: PartnerOrder["items"][number];
  index: number;
  disabled: boolean;
}) {
  const download = useDownload(order.id);
  const file = item.production_file;

  function get(kind: "3mf" | "image") {
    download.mutate(
      { kind: "item", itemId: item.id, file: kind },
      { onError: (error) => handleFormError(error) },
    );
  }

  return (
    <Card className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
      {/* eslint-disable-next-line @next/next/no-img-element -- imagem por URL assinada */}
      <img
        src={item.image_url}
        alt={`Imagem de referência do item ${index + 1}`}
        className="size-28 shrink-0 rounded-xl bg-sunken object-contain"
      />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="font-semibold">
          Item {index + 1}: {categoryLabel(item.category)}, {item.size_label}
        </p>
        <p className="text-sm text-muted">
          {item.quantity} {item.quantity === 1 ? "unidade" : "unidades"}, maior lado{" "}
          {Math.round(item.longest_side_mm / 10)} cm
        </p>
        <p className="text-sm text-muted">
          {file
            ? `Arquivo 3MF versão ${file.version}, de ${formatDate(file.uploaded_at)}`
            : "Arquivo 3MF ainda não enviado pela EuMini"}
        </p>
      </div>
      {!disabled && (
        <div className="flex flex-wrap gap-2 sm:flex-col">
          <Button
            variant="secondary"
            size="sm"
            disabled={!file}
            pending={
              download.isPending &&
              download.variables?.kind === "item" &&
              download.variables.file === "3mf"
            }
            onClick={() => get("3mf")}
          >
            <FileBox aria-hidden />
            Baixar 3MF
          </Button>
          <Button
            variant="secondary"
            size="sm"
            pending={
              download.isPending &&
              download.variables?.kind === "item" &&
              download.variables.file === "image"
            }
            onClick={() => get("image")}
          >
            <ImageIcon aria-hidden />
            Baixar imagem
          </Button>
        </div>
      )}
    </Card>
  );
}

function NextAction({ order }: { order: PartnerOrder }) {
  const router = useRouter();
  const actions = useOrderActions(order.id);
  const [refusing, setRefusing] = useState(false);
  const [reason, setReason] = useState("");
  const [posting, setPosting] = useState(false);
  const [photos, setPhotos] = useState<File[]>([]);
  const missingFile = order.items.some((item) => !item.production_file);

  if (order.group === "to_print") {
    return (
      <Card className="space-y-3 p-4">
        {missingFile && (
          <Callout tone="neutral">
            O arquivo de impressão ainda não chegou. Você pode iniciar quando a EuMini enviar.
          </Callout>
        )}
        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            variant="primary"
            disabled={missingFile}
            pending={actions.start.isPending}
            onClick={() =>
              actions.start.mutate(undefined, {
                onSuccess: () => toast.success("Produção iniciada. O cliente já vê o andamento."),
                onError: (error) => handleFormError(error),
              })
            }
          >
            Iniciar produção
          </Button>
          <Button variant="ghost" onClick={() => setRefusing(true)}>
            Não posso imprimir
          </Button>
        </div>
        <ConfirmDialog
          open={refusing}
          onOpenChange={setRefusing}
          title="Recusar este pedido?"
          description="Ele volta para a EuMini, que vai passar para outro parceiro."
          confirmLabel="Recusar pedido"
          tone="danger"
          pending={actions.refuse.isPending}
          onConfirm={() => {
            if (!reason.trim()) {
              toast.error("Conte o motivo da recusa.");
              return;
            }
            actions.refuse.mutate(reason.trim(), {
              onSuccess: () => {
                toast.success("Pedido recusado.");
                router.replace("/impressoes");
              },
              onError: (error) => handleFormError(error),
            });
          }}
        >
          <Label htmlFor="refuse-reason">Motivo</Label>
          <Textarea
            id="refuse-reason"
            className="mt-1.5"
            rows={3}
            maxLength={500}
            placeholder="Ex.: impressora parada, sem filamento da cor"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </ConfirmDialog>
      </Card>
    );
  }

  if (order.group === "in_production") {
    return (
      <Card className="space-y-3 p-4">
        <p className="font-semibold">Fotos das peças prontas</p>
        <p className="text-sm text-muted">
          Envie de 1 a {READY_PHOTOS_MAX} fotos com todas as peças, com boa luz. A EuMini usa as
          fotos para conferir a qualidade.
        </p>
        <PhotoPicker files={photos} onChange={setPhotos} max={READY_PHOTOS_MAX} />
        <Button
          variant="primary"
          disabled={photos.length === 0}
          pending={actions.ready.isPending}
          onClick={() =>
            actions.ready.mutate(photos, {
              onSuccess: () => {
                setPhotos([]);
                toast.success("Peças marcadas como prontas. Agora é com a etiqueta.");
              },
              onError: (error) => handleFormError(error),
            })
          }
        >
          Marcar como prontas
        </Button>
      </Card>
    );
  }

  if (order.group === "to_post") {
    return (
      <Card className="space-y-3 p-4">
        <Button variant="primary" onClick={() => setPosting(true)}>
          Marcar como postado
        </Button>
        <ConfirmDialog
          open={posting}
          onOpenChange={setPosting}
          title="Já postou o pedido?"
          description="Confirme só depois de entregar o pacote na agência ou na coleta. O cliente passa a ver o rastreio."
          confirmLabel="Sim, postei"
          pending={actions.post.isPending}
          onConfirm={() =>
            actions.post.mutate(undefined, {
              onSuccess: () => {
                setPosting(false);
                toast.success("Pedido postado. O ganho entrou no seu extrato.");
              },
              onError: (error) => handleFormError(error),
            })
          }
        />
      </Card>
    );
  }

  return null;
}

function LabelCard({ order }: { order: PartnerOrder }) {
  const download = useDownload(order.id);
  const label = order.label;
  if (!label) return null;

  return (
    <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-1">
        <p className="font-semibold">Etiqueta de envio</p>
        <p className="text-sm text-muted">
          {label.carrier}, rastreio{" "}
          <span className="font-mono text-ink">{label.tracking_code}</span>
        </p>
        {label.shipped_at && (
          <p className="text-sm text-muted">Postado em {formatDate(label.shipped_at)}</p>
        )}
      </div>
      {order.group !== "cancelled" && (
        <Button
          variant="secondary"
          pending={download.isPending}
          onClick={() =>
            download.mutate({ kind: "label" }, { onError: (error) => handleFormError(error) })
          }
        >
          <Download aria-hidden />
          Baixar etiqueta
        </Button>
      )}
    </Card>
  );
}

function Issues({ order, canReport }: { order: PartnerOrder; canReport: boolean }) {
  const actions = useOrderActions(order.id);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [photo, setPhoto] = useState<File[]>([]);

  if (!canReport && order.issues.length === 0) return null;

  return (
    <section aria-labelledby="problemas" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="problemas" className="font-display text-xl font-semibold">
          Problemas
        </h2>
        {canReport && (
          <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
            <TriangleAlert aria-hidden />
            Reportar problema
          </Button>
        )}
      </div>
      {order.issues.length === 0 && (
        <p className="text-sm text-muted">
          Arquivo com defeito ou impressão que falhou? Conte para a EuMini por aqui.
        </p>
      )}
      {order.issues.map((issue) => (
        <Card key={issue.id} className="space-y-2 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted">{formatDate(issue.created_at)}</span>
            <StatusBadge
              label={issue.resolved_at ? "Resolvido" : "Com a EuMini"}
              tone={issue.resolved_at ? "success" : "progress"}
            />
          </div>
          <p className="whitespace-pre-line text-sm">{issue.text}</p>
          {issue.photo_url && (
            // eslint-disable-next-line @next/next/no-img-element -- imagem por URL assinada
            <img src={issue.photo_url} alt="" className="size-24 rounded-xl object-cover" />
          )}
          {issue.resolution_note && (
            <p className="text-sm text-muted">Resposta: {issue.resolution_note}</p>
          )}
        </Card>
      ))}
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title="Reportar problema"
        description="A EuMini recebe o aviso e responde por aqui ou por e-mail."
        confirmLabel="Enviar"
        pending={actions.reportIssue.isPending}
        onConfirm={() => {
          if (!text.trim()) {
            toast.error("Conte o que aconteceu.");
            return;
          }
          actions.reportIssue.mutate(
            { text: text.trim(), photo: photo[0] ?? null },
            {
              onSuccess: () => {
                setOpen(false);
                setText("");
                setPhoto([]);
                toast.success("Problema enviado para a EuMini.");
              },
              onError: (error) => handleFormError(error),
            },
          );
        }}
      >
        <div className="space-y-3">
          <div>
            <Label htmlFor="issue-text">O que aconteceu?</Label>
            <Textarea
              id="issue-text"
              className="mt-1.5"
              rows={4}
              maxLength={2000}
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
          </div>
          <PhotoPicker files={photo} onChange={setPhoto} max={1} label="Anexar foto (opcional)" />
        </div>
      </ConfirmDialog>
    </section>
  );
}
