import { type NextRequest, NextResponse } from "next/server";

import { REFRESH_COOKIE } from "@eumini/web-core/auth-constants";

/**
 * Primeira barreira: sem cookie de sessão, todo o app leva ao login. A autorização de verdade
 * é sempre do backend, que confere o papel da equipe. A API fica fora do middleware, o que
 * também evita o limite de tamanho do corpo no envio do 3MF.
 */
export function middleware(request: NextRequest): NextResponse {
  if (request.cookies.has(REFRESH_COOKIE)) return NextResponse.next();
  const url = request.nextUrl.clone();
  url.pathname = "/entrar";
  url.search = `next=${encodeURIComponent(request.nextUrl.pathname)}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!entrar|recuperar-senha|bff|api|_next|brand|icon\\.svg|favicon).*)"],
};
