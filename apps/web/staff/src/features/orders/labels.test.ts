import { describe, expect, it } from "vitest";

import { QUEUE_ORDER, QUEUES, eventLabel } from "./labels";

describe("fila do dia", () => {
  it("mostra todos os grupos, cada um uma vez", () => {
    expect(new Set(QUEUE_ORDER)).toEqual(new Set(Object.keys(QUEUES)));
    expect(QUEUE_ORDER).toHaveLength(Object.keys(QUEUES).length);
  });

  it("traduz eventos conhecidos e mantém os desconhecidos", () => {
    expect(eventLabel("assign")).toBe("Atribuído ao parceiro");
    expect(eventLabel("algo_novo")).toBe("algo_novo");
    expect(eventLabel("pay", "charge")).toBe("Cobrança paga");
    expect(eventLabel("pay")).toBe("Pagamento confirmado");
  });
});
