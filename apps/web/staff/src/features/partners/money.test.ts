import { describe, expect, it } from "vitest";

import { centsToInput, parseBRL, selectedTotal } from "./money";

describe("repasse", () => {
  it("soma só os lançamentos escolhidos, inclusive ajustes negativos", () => {
    const entries = [
      { id: "a", amount_cents: 5000 },
      { id: "b", amount_cents: -500 },
      { id: "c", amount_cents: 7000 },
    ];
    expect(selectedTotal(entries, new Set(["a", "b"]))).toBe(4500);
    expect(selectedTotal(entries, new Set())).toBe(0);
  });

  it("lê valores em reais como centavos", () => {
    expect(parseBRL("129,90")).toBe(12990);
    expect(parseBRL("R$ 1.299,90")).toBe(129990);
    expect(parseBRL("-5")).toBe(-500);
    expect(parseBRL("abc")).toBeNull();
    expect(parseBRL("1,999")).toBeNull();
  });

  it("mostra centavos no formato do campo", () => {
    expect(centsToInput(12990)).toBe("129,90");
    expect(centsToInput(null)).toBe("");
  });
});
