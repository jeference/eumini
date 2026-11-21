"use client";

import { type Schemas, unwrap } from "@eumini/api-client";
import { qk, useApiClient } from "@eumini/api-client/react";
import { useQuery } from "@tanstack/react-query";

import type { Category } from "@/features/catalog/categories";

export type Product = Schemas["Product"];

/** Categorias à venda, com os tamanhos e preços de cada uma. */
export function useProducts() {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.products(),
    staleTime: 5 * 60 * 1000,
    queryFn: async () => unwrap(await api.GET("/api/catalog/products/")),
  });
}

export function useProduct(category: Category | "" | undefined): Product | undefined {
  const { data } = useProducts();
  return data?.find((product) => product.category === category);
}
