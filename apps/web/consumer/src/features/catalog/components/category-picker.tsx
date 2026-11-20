"use client";

import { track } from "@kubo/analytics";
import { Card } from "@kubo/ui/card";
import { formatBRL } from "@kubo/ui/lib/format";
import { ArrowRight, type LucideIcon, PawPrint, User, Users } from "lucide-react";
import Link from "next/link";

import { CATEGORIES, type Category } from "@/features/catalog/categories";
import { useProducts } from "@/features/catalog/hooks";

const ICONS: Record<Category, LucideIcon[]> = {
  person: [User],
  pet: [PawPrint],
  couple: [Users],
  person_pet: [User, PawPrint],
};

/** Vitrine: cada categoria leva à sua página de envio de foto. */
export function CategoryPicker() {
  const { data: products } = useProducts();
  const fromPrice = (category: Category) =>
    products?.find((product) => product.category === category)?.from_price_cents;

  return (
    <div className="mx-auto max-w-4xl" id="categorias">
      <h1 className="text-center font-display text-3xl font-semibold tracking-tight sm:text-4xl">
        Qual miniatura você quer?
      </h1>
      <p className="mt-2 text-center text-muted">
        Escolha, envie uma foto e veja a sua miniatura em segundos.
      </p>
      <ul className="mt-6 grid gap-3 sm:mt-8 sm:grid-cols-2">
        {CATEGORIES.map((category) => {
          const price = fromPrice(category.id);
          return (
            <li key={category.id}>
              <Card asChild>
                <Link
                  href={`/criar/${category.slug}`}
                  onClick={() => track("category_selected", { category: category.id })}
                  className="group flex items-center gap-4 p-4 transition-colors hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:p-5"
                >
                  <span className="flex size-14 shrink-0 items-center justify-center gap-0.5 rounded-2xl bg-accent-soft text-accent">
                    {ICONS[category.id].map((Icon, index) => (
                      <Icon key={index} className="size-6" aria-hidden />
                    ))}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-display text-lg font-semibold">
                      {category.label}
                    </span>
                    <span className="block text-sm text-muted">{category.hint}</span>
                    <span className="mt-1 block text-sm font-medium">
                      {price ? `A partir de ${formatBRL(price)}` : " "}
                    </span>
                  </span>
                  <ArrowRight
                    className="size-5 shrink-0 text-muted transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </Link>
              </Card>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
