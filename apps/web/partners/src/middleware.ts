import { type NextRequest, NextResponse } from "next/server";

import { REFRESH_COOKIE } from "@eumini/web-core/auth-constants";

/**
 * Primeira barreira: sem cookie de sessão, todo o app leva ao login. A autorização de verdade
 * é sempre do backend, que confere se a conta é de um parceiro ativo.
 */
export function middleware(request: NextRequest): NextResponse {
  if (request.cookies.has(REFRESH_COOKIE)) return NextResponse.next();
  const url = request.nextUrl.clone();
  url.pathname = "/entrar";
  url.search = `next=${encodeURIComponent(request.nextUrl.pathname)}`;
  return NextResponse.redirect(url);
}

export const config = {
  // Tudo, menos as telas de acesso, o BFF, a API e os arquivos estáticos.
  matcher: ["/((?!entrar|recuperar-senha|convite|bff|api|_next|brand|icon\\.svg|favicon).*)"],
};
