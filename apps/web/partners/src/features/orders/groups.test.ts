import { describe, expect, it } from "vitest";

import { GROUPS, TAB_ORDER, deadlineTone, isOrderGroup } from "./groups";

describe("grupos da fila", () => {
  it("tem uma aba para cada grupo", () => {
    expect(new Set(TAB_ORDER)).toEqual(new Set(Object.keys(GROUPS)));
  });

  it("aceita só grupos conhecidos na URL", () => {
    expect(isOrderGroup("to_post")).toBe(true);
    expect(isOrderGroup("qualquer")).toBe(false);
    expect(isOrderGroup(null)).toBe(false);
  });

  it("destaca o atraso antes do prazo próximo", () => {
    expect(deadlineTone({ is_overdue: true, is_due_soon: true })).toBe("danger");
    expect(deadlineTone({ is_overdue: false, is_due_soon: true })).toBe("progress");
    expect(deadlineTone({ is_overdue: false, is_due_soon: false })).toBe("neutral");
  });
});
