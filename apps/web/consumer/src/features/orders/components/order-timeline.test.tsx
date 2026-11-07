import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OrderTimeline } from "./order-timeline";

describe("OrderTimeline", () => {
  it("marca a etapa atual com a tag Em andamento", () => {
    const { container } = render(<OrderTimeline status="in_production" />);
    const current = container.querySelector('[aria-current="step"]');
    expect(current).toHaveTextContent("Em produção");
    expect(current).toHaveTextContent("Em andamento");
    expect(screen.getAllByText("Em andamento")).toHaveLength(1);
    expect(screen.getByText("Entregue")).toBeInTheDocument();
  });

  it("pedido confirmado não fica em andamento", () => {
    const { container } = render(<OrderTimeline status="paid" />);
    expect(container.querySelector('[aria-current="step"]')).toHaveTextContent("Confirmado");
    expect(screen.queryByText("Em andamento")).not.toBeInTheDocument();
  });

  it("não aparece em pedido encerrado sem produção", () => {
    const { container } = render(<OrderTimeline status="refunded" />);
    expect(container).toBeEmptyDOMElement();
  });
});
