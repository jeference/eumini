import type { Schemas } from "@eumini/api-client";

export type Category = Schemas["CategoryEnum"];
export type RejectionReason = Schemas["RejectionReasonEnum"];

type CategoryInfo = {
  id: Category;
  /** Endereço da página de entrada: `/criar/<slug>`. */
  slug: string;
  label: string;
  /** Título da página de entrada. */
  title: string;
  hint: string;
};

/** Na ordem da vitrine. Casal e Pessoa + Pet são uma peça só (RN-35). */
export const CATEGORIES: CategoryInfo[] = [
  {
    id: "person",
    slug: "pessoa",
    label: "Pessoa",
    title: "Envie a foto da pessoa",
    hint: "Uma pessoa, de corpo inteiro.",
  },
  {
    id: "pet",
    slug: "pet",
    label: "Pet",
    title: "Envie a foto do seu pet",
    hint: "Seu cachorro, gato ou outro bichinho.",
  },
  {
    id: "couple",
    slug: "casal",
    label: "Casal",
    title: "Envie a foto do casal",
    hint: "Duas pessoas, juntas numa peça só.",
  },
  {
    id: "person_pet",
    slug: "pessoa-pet",
    label: "Pessoa + Pet",
    title: "Envie a foto de você com seu pet",
    hint: "Uma pessoa e o pet, juntos numa peça só.",
  },
];

export function categoryBySlug(slug: string): CategoryInfo | undefined {
  return CATEGORIES.find((category) => category.slug === slug);
}

export function categoryInfo(id: Category): CategoryInfo {
  return CATEGORIES.find((category) => category.id === id) ?? CATEGORIES[0];
}

/** Recusas por gente ou pets demais: o cliente pode recortar ou entrar na lista de espera. */
export const GROUP_REASONS: ReadonlySet<RejectionReason> = new Set([
  "three_or_more_people",
  "multiple_pets",
  "group_with_pets",
]);

export const REJECTION_MESSAGES: Record<RejectionReason, string> = {
  three_or_more_people: "A foto tem 3 ou mais pessoas.",
  multiple_pets: "A foto tem mais de um pet.",
  group_with_pets: "A foto tem mais pessoas ou pets do que cabem numa peça.",
  no_subject: "Não encontramos uma pessoa ou um pet na foto.",
  protected_character: "A foto mostra um personagem ou uma marca conhecidos.",
};

/** Rótulo de uma categoria vinda como texto livre (carrinho e pedido). */
export function categoryLabel(id: string): string {
  return CATEGORIES.find((category) => category.id === id)?.label ?? id;
}
