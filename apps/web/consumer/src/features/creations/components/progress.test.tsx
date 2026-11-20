import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IMAGE_PROGRESS, PHOTO_PROGRESS, ProgressNotice } from "./progress";

describe("ProgressNotice", () => {
  it("avança as etapas com o tempo, sem porcentagem", () => {
    const { container } = render(<ProgressNotice progress={IMAGE_PROGRESS} elapsed={4} />);
    const current = container.querySelector('[aria-current="step"]');
    expect(current).toHaveTextContent("Rascunhando a miniatura");
    expect(container.textContent).not.toContain("%");
  });

  it("no último passo, troca a frase para não parecer travado", () => {
    render(<ProgressNotice progress={IMAGE_PROGRESS} elapsed={9 + 4} />);
    expect(screen.getByText("Ajustando a luz")).toBeInTheDocument();
  });

  it("lê a foto em poucos passos antes de gerar", () => {
    const { container } = render(<ProgressNotice progress={PHOTO_PROGRESS} elapsed={1} />);
    expect(screen.getByText("Lendo a foto")).toBeInTheDocument();
    const current = container.querySelector('[aria-current="step"]');
    expect(current).toHaveTextContent("Procurando pessoas e pets");
  });
});
