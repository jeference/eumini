import { describe, expect, it } from "vitest";

import { inviteSchema } from "./schemas";

describe("criar senha pelo convite", () => {
  it("exige as duas senhas iguais", () => {
    const result = inviteSchema.safeParse({ password: "Senha-forte-1", confirm: "outra" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0]?.path).toEqual(["confirm"]);
  });

  it("aceita senhas iguais com 8 ou mais caracteres", () => {
    expect(
      inviteSchema.safeParse({ password: "Senha-forte-1", confirm: "Senha-forte-1" }).success,
    ).toBe(true);
  });
});
