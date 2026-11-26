const isProduction = process.env.NODE_ENV === "production";

// Sem pagamento aqui: nenhum script ou frame de terceiros.
const contentSecurityPolicy = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  // Imagens e arquivos vêm do storage por URL assinada.
  "img-src 'self' data: blob: https:",
  "font-src 'self'",
  "connect-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Só na imagem Docker: no Windows, o modo standalone exige permissão para criar symlinks.
  output: process.env.NEXT_STANDALONE ? "standalone" : undefined,
  transpilePackages: [
    "@eumini/api-types",
    "@eumini/api-client",
    "@eumini/design-tokens",
    "@eumini/ui",
    "@eumini/web-core",
  ],
  // Com middleware, o Next guarda o corpo da requisição e corta em 10 MB por padrão, mesmo nas
  // rotas fora do matcher. O 3MF chega a 100 MB (PRODUCTION_FILE_MAX_BYTES no backend).
  experimental: { middlewareClientMaxBodySize: "110mb" },
  // O navegador fica na mesma origem, sem CORS. As rotas do Django terminam em barra: evitamos
  // o redirecionamento do Next e devolvemos a barra no destino.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const django = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${django}/api/:path*/` }];
  },
  async headers() {
    const security = [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    ];
    if (isProduction) {
      security.push({ key: "Content-Security-Policy", value: contentSecurityPolicy });
    }
    return [{ source: "/:path*", headers: security }];
  },
};

export default nextConfig;
