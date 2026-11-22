import { NextResponse } from "next/server";

import { env } from "../env";
import { VISITOR_COOKIE } from "./constants";
import {
  clearRefreshCookie,
  getRefreshCookie,
  getVisitorCookie,
  setRefreshCookie,
  setVisitorCookie,
} from "./cookies";

/**
 * Corpo dos route handlers do BFF. Cada app expõe as rotas com reexports de uma linha, então
 * os apps têm BFFs idênticos em `/bff/*`. O access token volta ao navegador; o refresh, não.
 */

/**
 * Repassa ao Django o IP do visitante. Sem isto, toda chamada do BFF chega com o IP do Next e
 * os limites por IP passam a valer para todos os visitantes juntos. Em produção o Django usa o
 * `cf-connecting-ip`, gravado pela Cloudflare; localmente, o `x-forwarded-for`.
 */
/**
 * Barra chamadas vindas de outro site. Sem isto, um formulário em outro domínio faria login do
 * visitante na conta do atacante ou trocaria o cookie de visitante (CSRF). Os navegadores mandam
 * `Sec-Fetch-Site` e `Origin` em POSTs; sem nenhum dos dois (curl, testes), a chamada segue.
 */
function rejectCrossSite(request: Request): NextResponse | null {
  const forbidden = NextResponse.json({ detail: "Origem não permitida." }, { status: 403 });
  if (request.headers.get("sec-fetch-site") === "cross-site") return forbidden;
  const origin = request.headers.get("origin");
  if (!origin) return null;
  try {
    return new URL(origin).host === request.headers.get("host") ? null : forbidden;
  } catch {
    return forbidden;
  }
}

function clientIpHeaders(request: Request): Record<string, string> {
  const headers: Record<string, string> = {};
  for (const name of ["x-forwarded-for", "cf-connecting-ip"]) {
    const value = request.headers.get(name);
    if (value) headers[name] = value;
  }
  return headers;
}

export async function bffLogin(request: Request): Promise<NextResponse> {
  const blocked = rejectCrossSite(request);
  if (blocked) return blocked;
  const body = (await request.json().catch(() => null)) as unknown;
  const response = await fetch(`${env.djangoUrl}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...clientIpHeaders(request) },
    body: JSON.stringify(body ?? {}),
  });
  const data = (await response.json().catch(() => ({}))) as { access?: string; refresh?: string };

  if (!response.ok) return NextResponse.json(data, { status: response.status });
  if (!data.access || !data.refresh) {
    return NextResponse.json({ detail: "Resposta de login inválida." }, { status: 502 });
  }
  await setRefreshCookie(data.refresh);
  return NextResponse.json({ access: data.access });
}

export async function bffRefresh(request: Request): Promise<NextResponse> {
  const blocked = rejectCrossSite(request);
  if (blocked) return blocked;
  const refresh = await getRefreshCookie();
  // Visitante sem conta é o caso comum, não um erro.
  if (!refresh) return NextResponse.json({ access: null });

  const response = await fetch(`${env.djangoUrl}/api/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...clientIpHeaders(request) },
    body: JSON.stringify({ refresh }),
  });
  const data = (await response.json().catch(() => ({}))) as { access?: string; refresh?: string };

  if (!response.ok || !data.access) {
    await clearRefreshCookie();
    return NextResponse.json({ detail: "Sessão expirada." }, { status: 401 });
  }
  if (data.refresh) await setRefreshCookie(data.refresh); // Refresh rotativo.
  return NextResponse.json({ access: data.access });
}

export async function bffLogout(request: Request): Promise<NextResponse> {
  const blocked = rejectCrossSite(request);
  if (blocked) return blocked;
  const refresh = await getRefreshCookie();
  if (refresh) {
    await fetch(`${env.djangoUrl}/api/auth/logout/`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...clientIpHeaders(request) },
      body: JSON.stringify({ refresh }),
    }).catch(() => undefined);
  }
  await clearRefreshCookie();
  return NextResponse.json({ ok: true });
}

export async function bffVerifyEmail(request: Request): Promise<NextResponse> {
  const blocked = rejectCrossSite(request);
  if (blocked) return blocked;
  const body = (await request.json().catch(() => null)) as unknown;
  const response = await fetch(`${env.djangoUrl}/api/auth/verify-email/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...clientIpHeaders(request) },
    body: JSON.stringify(body ?? {}),
  });
  const data = (await response.json().catch(() => ({}))) as {
    user?: unknown;
    tokens?: { access?: string; refresh?: string };
  };

  if (!response.ok) return NextResponse.json(data, { status: response.status });
  if (!data.tokens?.access || !data.tokens.refresh) {
    return NextResponse.json({ detail: "Resposta de verificação inválida." }, { status: 502 });
  }
  await setRefreshCookie(data.tokens.refresh);
  return NextResponse.json({ access: data.tokens.access, user: data.user });
}

/** Garante o cookie de visitante. Se o token não vale mais, cria outro. */
export async function bffVisitor(request: Request): Promise<NextResponse> {
  const blocked = rejectCrossSite(request);
  if (blocked) return blocked;
  const current = await getVisitorCookie();
  if (current) {
    const check = await fetch(`${env.djangoUrl}/api/quota/`, {
      headers: { Cookie: `${VISITOR_COOKIE}=${current}` },
    }).catch(() => null);
    if (!check || check.ok || check.status >= 500) return NextResponse.json({ ok: true });
  }
  const response = await fetch(`${env.djangoUrl}/api/visitors/`, {
    method: "POST",
    headers: clientIpHeaders(request),
  }).catch(() => null);
  if (!response?.ok) return NextResponse.json({ ok: false }, { status: 503 });
  const data = (await response.json()) as { token: string };
  await setVisitorCookie(data.token);
  return NextResponse.json({ ok: true });
}
