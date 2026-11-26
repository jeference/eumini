import { formatBRL, formatDate, formatDay } from "@eumini/ui/lib/format";
import { ORDER_STATUS } from "@eumini/ui/lib/status";
import { StatusBadge } from "@eumini/ui/status-badge";
import { ChevronRight, TriangleAlert } from "lucide-react";
import Link from "next/link";

import { STAGES } from "../labels";
import type { StaffOrderRow } from "../hooks";

export function OrderRow({ order }: { order: StaffOrderRow }) {
  const status = ORDER_STATUS[order.status];
  const stage = STAGES[order.stage];
  const inProduction = order.status === "paid" || order.status === "in_production";

  return (
    <Link
      href={`/pedidos/${order.id}`}
      className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-3 shadow-card transition-colors hover:border-accent"
    >
      {order.thumbnail_url ? (
        // eslint-disable-next-line @next/next/no-img-element -- imagem por URL assinada
        <img
          src={order.thumbnail_url}
          alt=""
          className="size-14 shrink-0 rounded-xl bg-sunken object-contain"
        />
      ) : (
        <span className="size-14 shrink-0 rounded-xl bg-sunken" />
      )}
      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-semibold">{order.number}</span>
          {order.open_issues > 0 && (
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-danger">
              <TriangleAlert className="size-3.5" aria-hidden />
              {order.open_issues} {order.open_issues === 1 ? "problema" : "problemas"}
            </span>
          )}
        </span>
        <span className="block truncate text-sm text-muted">
          {order.customer_name}, {order.piece_count} {order.piece_count === 1 ? "peça" : "peças"}
          {order.partner && `, com ${order.partner.name}`}
        </span>
        <span className="block text-xs text-muted">
          {formatDate(order.created_at)}
          {inProduction && order.post_by && (
            <span className={order.is_overdue ? "font-semibold text-danger" : ""}>
              {" "}
              · postar até {formatDay(order.post_by)}
            </span>
          )}
        </span>
      </span>
      <span className="hidden flex-col items-end gap-1 sm:flex">
        <StatusBadge label={status.label} tone={status.tone} />
        {inProduction && <StatusBadge label={stage.label} tone={stage.tone} />}
        <span className="text-sm font-semibold tabular-nums">{formatBRL(order.total_cents)}</span>
      </span>
      <ChevronRight className="size-5 shrink-0 text-muted" aria-hidden />
    </Link>
  );
}
