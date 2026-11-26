import { describe, expect, it } from "vitest";

import { safeNext } from "./safe-next";

const HOME = "/inicio";

describe("safeNext", () => {
  it("aceita caminho interno", () => {
    expect(safeNext("/checkout", HOME)).toBe("/checkout");
  });

  it("recusa endereço externo", () => {
    expect(safeNext("https://malicioso.com", HOME)).toBe(HOME);
    expect(safeNext("//malicioso.com", HOME)).toBe(HOME);
    expect(safeNext(null, HOME)).toBe(HOME);
  });

  it("recusa barra invertida e caracteres de controle, que o navegador normaliza para //", () => {
    expect(safeNext("/\\malicioso.com", HOME)).toBe(HOME);
    expect(safeNext("/\t/malicioso.com", HOME)).toBe(HOME);
    expect(safeNext("/\n/malicioso.com", HOME)).toBe(HOME);
  });
});
