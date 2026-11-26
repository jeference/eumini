const LABELS: Record<string, string> = {
  person: "Pessoa",
  pet: "Pet",
  couple: "Casal",
  person_pet: "Pessoa + Pet",
};

/** Rótulo da categoria, que vem do pedido como texto. */
export function categoryLabel(id: string): string {
  return LABELS[id] ?? id;
}
