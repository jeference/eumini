"use client";

import { unwrap } from "@eumini/api-client";
import { qk, useApiClient } from "@eumini/api-client/react";
import { useSession } from "@eumini/web-core/session";
import { useQuery } from "@tanstack/react-query";

function useAuthenticated(): boolean {
  return useSession((state) => state.status === "authenticated");
}

export function useBalance() {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.partnerEarnings(),
    enabled: useAuthenticated(),
    queryFn: async () => unwrap(await api.GET("/api/partner/earnings/")),
  });
}

export function useEntries(page: number) {
  const api = useApiClient();
  return useQuery({
    queryKey: [...qk.partnerEntries(), page],
    enabled: useAuthenticated(),
    queryFn: async () =>
      unwrap(await api.GET("/api/partner/earnings/entries/", { params: { query: { page } } })),
  });
}

export function usePayouts() {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.partnerPayouts(),
    enabled: useAuthenticated(),
    queryFn: async () => unwrap(await api.GET("/api/partner/payouts/")),
  });
}
