import { formatDay } from "@eumini/ui/lib/format";
import { StatusBadge } from "@eumini/ui/status-badge";
import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { GROUPS } from "../groups";
import type { PartnerOrderRow } from "../hooks";
import { DeadlineBadge } from "./deadline-badge";

export function OrderRow({ order }: { order: PartnerOrderRow }) {
  const group = GROUPS[order.group];
  const active = order.group !== "posted" && order.group !== "cancelled";

  return (
    <Link
      href={`/impressoes/${order.id}`}
      className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-3 shadow-card transition-colors hover:border-accent"
    >
      {order.thumbnail_url ? (
        // eslint-disable-next-line @next/next/no-img-element -- imagem dinâmica, por URL assinada
        <img
          src={order.thumbnail_url}
          alt=""
          className="size-16 shrink-0 rounded-xl bg-sunken object-contain"
        />
      ) : (
        <span className="size-16 shrink-0 rounded-xl bg-sunken" />
      )}
      <span className="min-w-0 flex-1">
        <span className="block font-semibold">{order.number}</span>
        <span className="block text-sm text-muted">
          {order.piece_count} {order.piece_count === 1 ? "peça" : "peças"}
          {!active && order.post_by && `, prazo era ${formatDay(order.post_by)}`}
        </span>
      </span>
      <span className="flex flex-col items-end gap-1">
        {active ? (
          <DeadlineBadge order={order} />
        ) : (
          <StatusBadge label={group.label} tone={group.tone} />
        )}
      </span>
      <ChevronRight className="size-5 shrink-0 text-muted" aria-hidden />
    </Link>
  );
}
