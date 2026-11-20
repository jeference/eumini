import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { CATEGORIES, categoryBySlug } from "@/features/catalog/categories";
import { PromptStep } from "@/features/creations/components/prompt-step";

type Params = { params: Promise<{ categoria: string }> };

export function generateStaticParams() {
  return CATEGORIES.map((category) => ({ categoria: category.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const category = categoryBySlug((await params).categoria);
  return { title: category ? `Miniatura ${category.label}` : "Criar" };
}

/** Página de entrada de uma categoria. A categoria é só uma sugestão: o classificador decide. */
export default async function CreateCategoryPage({ params }: Params) {
  const category = categoryBySlug((await params).categoria);
  if (!category) notFound();
  return <PromptStep category={category.id} />;
}
