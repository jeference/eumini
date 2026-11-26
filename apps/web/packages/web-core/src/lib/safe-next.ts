/**
 * Só caminhos internos: impede redirecionamento para outro site.
 *
 * Além de "//", o navegador trata "\" como "/" ("/\site.com" vira "//site.com"), e ignora
 * tabulações e quebras de linha no meio do endereço. Por isso a barra invertida e caracteres de
 * controle invalidam o valor inteiro. `fallback` é a página inicial de cada app.
 */
export function safeNext(value: string | null, fallback: string): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return fallback;
  if (/[\\\u0000-\u001f\u007f]/.test(value)) return fallback;
  return value;
}
