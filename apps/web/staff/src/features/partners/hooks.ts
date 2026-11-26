"use client";

import { type Schemas, unwrap } from "@eumini/api-client";
import { qk, useApiClient } from "@eumini/api-client/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuthenticated } from "@/features/orders/hooks";
import { multipart } from "@/lib/download";

export type StaffPartner = Schemas["StaffPartner"];
export type PartnerEntry = Schemas["PartnerEntry"];

export function usePartners() {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.staffPartners(),
    enabled: useAuthenticated(),
    queryFn: async () =>
      unwrap(await api.GET("/api/staff/partners/", { params: { query: { page_size: 100 } } })),
  });
}

export function usePartner(id: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.staffPartner(id),
    enabled: useAuthenticated(),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/staff/partners/{partner_id}/", {
          params: { path: { partner_id: id } },
        }),
      ),
  });
}

export function usePartnerEntries(id: string, open: boolean) {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.staffPartnerEntries(id, open),
    enabled: useAuthenticated(),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/staff/partners/{partner_id}/entries/", {
          params: {
            path: { partner_id: id },
            query: { page_size: 100, ...(open ? { aberto: "1" as const } : {}) },
          },
        }),
      ),
  });
}

export function usePartnerPayouts(id: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.staffPartnerPayouts(id),
    enabled: useAuthenticated(),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/staff/partners/{partner_id}/payouts/", {
          params: { path: { partner_id: id } },
        }),
      ),
  });
}

export function useCreatePartner() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas["PartnerCreateRequest"]) =>
      unwrap(await api.POST("/api/staff/partners/", { body })),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: qk.staffPartners() }),
  });
}

export function usePartnerActions(id: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const path = { params: { path: { partner_id: id } } };

  function settle(partner?: StaffPartner) {
    if (partner) queryClient.setQueryData(qk.staffPartner(id), partner);
    void queryClient.invalidateQueries({ queryKey: qk.staff() });
  }

  return {
    update: useMutation({
      mutationFn: async (body: Schemas["PatchedPartnerUpdateRequest"]) =>
        unwrap(await api.PATCH("/api/staff/partners/{partner_id}/", { ...path, body })),
      onSuccess: settle,
    }),
    invite: useMutation({
      mutationFn: async () => {
        unwrap(await api.POST("/api/staff/partners/{partner_id}/invite/", path));
      },
    }),
    deactivate: useMutation({
      mutationFn: async () =>
        unwrap(await api.POST("/api/staff/partners/{partner_id}/deactivate/", path)),
      onSuccess: settle,
    }),
    reactivate: useMutation({
      mutationFn: async () =>
        unwrap(await api.POST("/api/staff/partners/{partner_id}/reactivate/", path)),
      onSuccess: settle,
    }),
    payout: useMutation({
      mutationFn: async (input: {
        entryIds: string[];
        paidOn: string;
        amountCents: number;
        note: string;
        receipt?: File | null;
      }) =>
        unwrap(
          await api.POST("/api/staff/partners/{partner_id}/payouts/", {
            ...path,
            ...multipart({
              entry_ids: input.entryIds,
              paid_on: input.paidOn,
              amount_cents: String(input.amountCents),
              note: input.note,
              receipt: input.receipt ?? undefined,
            }),
          }),
        ),
      onSuccess: () => settle(),
    }),
    adjustment: useMutation({
      mutationFn: async (input: { amountCents: number; note: string }) =>
        unwrap(
          await api.POST("/api/staff/partners/{partner_id}/adjustments/", {
            ...path,
            body: { amount_cents: input.amountCents, note: input.note },
          }),
        ),
      onSuccess: () => settle(),
    }),
  };
}

export function useRates() {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.staffRates(),
    enabled: useAuthenticated(),
    queryFn: async () => unwrap(await api.GET("/api/staff/rates/")),
  });
}

export function useSaveRates() {
  const api = useApiClient();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (rates: Schemas["RateInputRequest"][]) =>
      unwrap(await api.PUT("/api/staff/rates/", { body: { rates } })),
    onSuccess: (rows) => queryClient.setQueryData(qk.staffRates(), rows),
  });
}
