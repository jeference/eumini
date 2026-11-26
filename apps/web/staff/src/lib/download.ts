/** Abre o download de uma URL assinada, com o nome de arquivo dado pelo servidor. */
export function openDownload({ url, filename }: { url: string; filename: string }): void {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

/** Corpo multipart para o cliente tipado, que por padrão serializa em JSON. */
export function multipart(fields: Record<string, string | Blob | (string | Blob)[] | undefined>) {
  const form = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    if (value === undefined) continue;
    for (const item of Array.isArray(value) ? value : [value]) form.append(key, item);
  }
  return {
    body: form as never,
    bodySerializer: (body: unknown) => body as FormData,
  };
}
