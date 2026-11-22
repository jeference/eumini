import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { store } = vi.hoisted(() => ({ store: new Map<string, string>() }));

vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => (store.has(name) ? { value: store.get(name) } : undefined),
    set: (name: string, value: string) => store.set(name, value),
  }),
}));

import { REFRESH_COOKIE } from "./constants";
import { bffLogin, bffLogout, bffRefresh } from "./bff-auth";

const fetchMock = vi.fn();

function request(headers: Record<string, string> = {}): Request {
  return new Request("https://eumini.com/bff/auth/x", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify({ email: "a@b.com", password: "x" }),
  });
}

function sentHeaders(): Record<string, string> {
  const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
  return init.headers as Record<string, string>;
}

beforeEach(() => {
  store.clear();
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ access: "a", refresh: "r" }), { status: 200 }),
  );
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("IP do visitante repassado ao Django", () => {
  const visitor = { "cf-connecting-ip": "203.0.113.7", "x-forwarded-for": "203.0.113.7" };

  it("no login", async () => {
    await bffLogin(request(visitor));
    expect(sentHeaders()).toMatchObject(visitor);
  });

  it("no refresh, que tem limite por IP", async () => {
    store.set(REFRESH_COOKIE, "r0");
    await bffRefresh(request(visitor));
    expect(sentHeaders()).toMatchObject(visitor);
  });

  it("no logout", async () => {
    store.set(REFRESH_COOKIE, "r0");
    await bffLogout(request(visitor));
    expect(sentHeaders()).toMatchObject(visitor);
  });

  it("recusa chamada de outro site, sem chegar ao Django", async () => {
    const fromOtherSite = await bffLogin(
      request({ origin: "https://malicioso.com", host: "eumini.com" }),
    );
    expect(fromOtherSite.status).toBe(403);
    const crossSite = await bffLogin(request({ "sec-fetch-site": "cross-site" }));
    expect(crossSite.status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("aceita chamada do próprio site", async () => {
    const response = await bffLogin(
      request({
        origin: "https://eumini.com",
        host: "eumini.com",
        "sec-fetch-site": "same-origin",
      }),
    );
    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("sem cabeçalhos de IP, não inventa valores", async () => {
    await bffLogin(request());
    expect(sentHeaders()).not.toHaveProperty("cf-connecting-ip");
    expect(sentHeaders()).not.toHaveProperty("x-forwarded-for");
  });
});
