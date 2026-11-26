"use client";

import { unwrap } from "@eumini/api-client";
import { qk, useApiClient } from "@eumini/api-client/react";
import { useSession } from "@eumini/web-core/session";
import { useQuery } from "@tanstack/react-query";

/** O parceiro da conta. 403 quando a conta não é de um parceiro ativo. */
export function usePartnerMe() {
  const api = useApiClient();
  const authenticated = useSession((state) => state.status === "authenticated");
  return useQuery({
    queryKey: qk.partnerMe(),
    enabled: authenticated,
    queryFn: async () => unwrap(await api.GET("/api/partner/me/")),
  });
}
