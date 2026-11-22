const isProduction = process.env.NODE_ENV === "production";

// Cartão: o abacatepay.js carrega o provedor dele (Rinne), que carrega o Evervault. O Evervault
// desenha os campos do cartão em iframes e cada um fala com a própria API.
const cardScripts = "https://abacatepay.com https://pkgs.rinne.com.br https://*.evervault.com";
const cardApis = "https://api.abacatepay.com https://*.rinne.com.br https://*.evervault.com";

const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' ${cardScripts}`,
  "style-src 'self' 'unsafe-inline'",
  // As imagens vêm do storage por URL assinada.
  "img-src 'self' data: blob: https:",
  "font-src 'self'",
  `connect-src 'self' ${cardApis}`,
  // Campos do cartão (Evervault) e o 3DS, que abre a página do banco do cliente: qualquer
  // domínio do banco, então só exigimos https.
  "frame-src https:",
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
    "@eumini/analytics",
  ],
  // O navegador fica na mesma origem, sem CORS. As rotas do Django terminam em barra: evitamos
  // o redirecionamento do Next e devolvemos a barra no destino.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const django = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${django}/api/:path*/` }];
  },
  // Um endereço só: www.<domínio> vai para <domínio>, preservando o caminho.
  async redirects() {
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "www\\.(?<domain>.+)" }],
        destination: "https://:domain/:path*",
        permanent: true,
      },
    ];
  },
  async headers() {
    const security = [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    ];
    if (isProduction) {
      security.push({ key: "Content-Security-Policy", value: contentSecurityPolicy });
    }
    return [
      { source: "/:path*", headers: security },
      // O token do acompanhamento está na URL: não pode vazar em cabeçalhos.
      {
        source: "/acompanhar/:token*",
        headers: [{ key: "Referrer-Policy", value: "no-referrer" }],
      },
    ];
  },
};

export default nextConfig;
