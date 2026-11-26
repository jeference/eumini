import { formatDay } from "@eumini/ui/lib/format";
import { StatusBadge } from "@eumini/ui/status-badge";

import { deadlineTone } from "../groups";

/** Prazo de postagem, com destaque para atraso e para o que vence em até 2 dias. */
export function DeadlineBadge({
  order,
}: {
  order: { post_by: string | null; is_overdue: boolean; is_due_soon: boolean };
}) {
  if (!order.post_by) return null;
  const day = formatDay(order.post_by);
  const label = order.is_overdue ? `Atrasado: era ${day}` : `Postar até ${day}`;
  return <StatusBadge label={label} tone={deadlineTone(order)} />;
}
