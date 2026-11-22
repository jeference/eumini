import { describe, expect, it } from "vitest";

import { safeNext } from "./safe-next";

describe("safeNext", () => {
  it("aceita caminho interno", () => {
    expect(safeNext("/checkout")).toBe("/checkout");
  });

  it("recusa endereço externo", () => {
    expect(safeNext("https://malicioso.com")).toBe("/criacoes");
    expect(safeNext("//malicioso.com")).toBe("/criacoes");
    expect(safeNext(null)).toBe("/criacoes");
  });

  it("recusa barra invertida e caracteres de controle, que o navegador normaliza para //", () => {
    expect(safeNext("/\\malicioso.com")).toBe("/criacoes");
    expect(safeNext("/\t/malicioso.com")).toBe("/criacoes");
    expect(safeNext("/\n/malicioso.com")).toBe("/criacoes");
  });
});
