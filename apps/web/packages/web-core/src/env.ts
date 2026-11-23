const DJANGO_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const env = {
  /** Origem do Django. O Next reescreve /api/* para cá; código de servidor chama direto. */
  djangoUrl: DJANGO_URL,
  /**
   * Bucket público com as imagens da própria plataforma (nunca arquivos de cliente). É o mesmo
   * em todos os ambientes, por isso não é variável.
   */
  assetsUrl: "https://eumini-assets.s3.sa-east-1.amazonaws.com",
} as const;

/** O navegador fala sempre com a mesma origem, então não há CORS. */
export function apiBaseUrl(): string {
  return typeof window === "undefined" ? DJANGO_URL : window.location.origin;
}
