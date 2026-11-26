/** Rótulos das categorias vendidas (RN-30). O consumer tem o catálogo completo, com imagens. */
export const CATEGORY_LABEL: Record<string, string> = {
  person: "Pessoa",
  pet: "Pet",
  couple: "Casal",
  person_pet: "Pessoa + Pet",
};

/** Rótulo da categoria, que vem do pedido como texto. */
export function categoryLabel(id: string): string {
  return CATEGORY_LABEL[id] ?? id;
}
