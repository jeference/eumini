import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Creation } from "@/features/creations/types";

import { RejectionMessage, isGroupRejection } from "./rejection";

function rejected(reason: Creation["rejection_reason"]): Creation {
  return {
    id: "c1",
    status: "rejected",
    requested_category: "couple",
    category: "",
    rejection_reason: reason,
    versions: [],
    edit_tasks: [],
  } as unknown as Creation;
}

describe("RejectionMessage", () => {
  it("foto com gente demais: pede o recorte e volta à página da categoria", () => {
    render(<RejectionMessage creation={rejected("three_or_more_people")} />);
    expect(screen.getByText("Recorte e nós fazemos")).toBeInTheDocument();
    expect(screen.getByText(/3 ou mais pessoas/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Enviar foto recortada/ })).toHaveAttribute(
      "href",
      "/criar/casal",
    );
    expect(isGroupRejection(rejected("three_or_more_people"))).toBe(true);
  });

  it("sem pessoa nem pet: pede outra foto, sem lista de espera", () => {
    render(<RejectionMessage creation={rejected("no_subject")} />);
    expect(screen.getByText("Precisamos de uma pessoa ou um pet na foto")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Escolher outra foto/ })).toBeInTheDocument();
    expect(isGroupRejection(rejected("no_subject"))).toBe(false);
  });
});
