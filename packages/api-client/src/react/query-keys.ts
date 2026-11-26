/** Chaves do React Query em um só lugar, para a invalidação ser previsível. */
export const qk = {
  me: () => ["me"] as const,
  addresses: () => ["me", "addresses"] as const,
  quota: () => ["quota"] as const,
  products: () => ["catalog", "products"] as const,
  creations: () => ["creations"] as const,
  creation: (id: string) => ["creations", id] as const,
  cart: () => ["cart"] as const,
  orders: () => ["orders"] as const,
  order: (id: string) => ["orders", id] as const,
  tracking: (token: string) => ["tracking", token] as const,
  // App de parceiros: tudo sob "partner", para invalidar de uma vez após cada ação.
  partner: () => ["partner"] as const,
  partnerMe: () => ["partner", "me"] as const,
  partnerOrders: (group: string) => ["partner", "orders", group] as const,
  partnerSummary: () => ["partner", "orders", "summary"] as const,
  partnerOrder: (id: string) => ["partner", "order", id] as const,
  partnerEarnings: () => ["partner", "earnings"] as const,
  partnerEntries: () => ["partner", "earnings", "entries"] as const,
  partnerPayouts: () => ["partner", "payouts"] as const,
};
