"use client";

import { type Schemas, unwrap } from "@eumini/api-client";
import { qk, useApiClient } from "@eumini/api-client/react";
import { stableUrl } from "@eumini/web-core/lib/stable-url";
import { useSession } from "@eumini/web-core/session";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { multipart, openDownload } from "@/lib/download";

import type { Queue } from "./labels";

export type StaffOrder = Schemas["StaffOrderDetail"];
export type StaffOrderRow = Schemas["StaffOrderList"];
export type OrderFilters = {
  fila?: Queue;
  status?: Schemas["OrderStatusEnum"];
  q?: string;
  parceiro?: string;
  desde?: string;
  ate?: string;
  page?: number;
};

/** A operação vê mudanças do parceiro e do pagamento sem recarregar. */
const POLL_MS = 30_000;

export function useAuthenticated(): boolean {
  return useSession((state) => state.status === "authenticated");
}

export function useQueueSummary() {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.staffSummary(),
    enabled: useAuthenticated(),
    refetchInterval: POLL_MS,
    queryFn: async () => unwrap(await api.GET("/api/staff/orders/summary/")),
  });
}

export function useOrders(filters: OrderFilters) {
  const api = useApiClient();
  const key = Object.fromEntries(
    Object.entries(filters)
      .filter(([, value]) => value !== undefined && value !== "")
      .map(([name, value]) => [name, String(value)]),
  );
  return useQuery({
    queryKey: qk.staffOrders(key),
    enabled: useAuthenticated(),
    refetchInterval: POLL_MS,
    queryFn: async () =>
      unwrap(await api.GET("/api/staff/orders/", { params: { query: filters } })),
    select: (page) => ({
      ...page,
      results: page.results.map((row) => ({
        ...row,
        thumbnail_url: stableUrl(`thumb:${row.id}`, row.thumbnail_url),
      })),
    }),
  });
}

function withStableUrls(order: StaffOrder): StaffOrder {
  return {
    ...order,
    thumbnail_url: stableUrl(`thumb:${order.id}`, order.thumbnail_url),
    items: order.items.map((item) => ({
      ...item,
      image_url: stableUrl(`item:${item.id}`, item.image_url),
      photo_url: stableUrl(`photo:${item.id}`, item.photo_url),
    })),
    photos: order.photos.map((photo) => ({ ...photo, url: stableUrl(photo.id, photo.url) })),
    issues: order.issues.map((issue) => ({
      ...issue,
      photo_url: stableUrl(`issue:${issue.id}`, issue.photo_url),
    })),
  };
}

export function useOrder(id: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.staffOrder(id),
    enabled: useAuthenticated(),
    refetchInterval: POLL_MS,
    staleTime: 0,
    queryFn: async () =>
      unwrap(
        await api.GET("/api/staff/orders/{order_id}/", { params: { path: { order_id: id } } }),
      ),
    select: withStableUrls,
  });
}

export function useOrderEvents(id: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.staffOrderEvents(id),
    enabled: useAuthenticated(),
    queryFn: async () =>
      unwrap(
        await api.GET("/api/staff/orders/{order_id}/events/", {
          params: { path: { order_id: id } },
        }),
      ),
  });
}

/** Ações do pedido. Cada uma devolve o pedido atualizado e invalida filas e histórico. */
export function useOrderActions(id: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const path = { params: { path: { order_id: id } } };

  function settle(order: StaffOrder) {
    queryClient.setQueryData(qk.staffOrder(id), order);
    void queryClient.invalidateQueries({ queryKey: qk.staff() });
  }

  return {
    assign: useMutation({
      mutationFn: async (input: { partnerId: string; reason?: string }) =>
        unwrap(
          await api.POST("/api/staff/orders/{order_id}/assign/", {
            ...path,
            body: { partner_id: input.partnerId, reason: input.reason ?? "" },
          }),
        ),
      onSuccess: settle,
    }),
    unassign: useMutation({
      mutationFn: async (reason: string) =>
        unwrap(
          await api.POST("/api/staff/orders/{order_id}/unassign/", { ...path, body: { reason } }),
        ),
      onSuccess: settle,
    }),
    uploadFile: useMutation({
      mutationFn: async (input: { itemId: string; file: File }) =>
        unwrap(
          await api.POST("/api/staff/orders/{order_id}/items/{item_id}/files/", {
            params: { path: { order_id: id, item_id: input.itemId } },
            ...multipart({ file: input.file }),
          }),
        ),
      onSuccess: settle,
    }),
    attachLabel: useMutation({
      mutationFn: async (input: { pdf: File; carrier: string; trackingCode: string }) =>
        unwrap(
          await api.POST("/api/staff/orders/{order_id}/label/", {
            ...path,
            ...multipart({
              pdf: input.pdf,
              carrier: input.carrier,
              tracking_code: input.trackingCode,
            }),
          }),
        ),
      onSuccess: settle,
    }),
    deliver: useMutation({
      mutationFn: async () => unwrap(await api.POST("/api/staff/orders/{order_id}/deliver/", path)),
      onSuccess: settle,
    }),
    resolveIssue: useMutation({
      mutationFn: async (input: { issueId: string; note: string }) =>
        unwrap(
          await api.POST("/api/staff/issues/{issue_id}/resolve/", {
            params: { path: { issue_id: input.issueId } },
            body: { note: input.note },
          }),
        ),
      onSuccess: settle,
    }),
  };
}

/** Pede a URL assinada (o download fica registrado) e abre o arquivo. */
export function useOrderDownload(orderId: string) {
  const api = useApiClient();
  return useMutation({
    mutationFn: async (
      target: { kind: "item"; itemId: string; file: "image" | "photo" | "3mf" } | { kind: "label" },
    ) => {
      if (target.kind === "label") {
        return unwrap(
          await api.POST("/api/staff/orders/{order_id}/label/download/", {
            params: { path: { order_id: orderId } },
          }),
        );
      }
      return unwrap(
        await api.POST("/api/staff/orders/{order_id}/items/{item_id}/download/", {
          params: { path: { order_id: orderId, item_id: target.itemId } },
          body: { file: target.file },
        }),
      );
    },
    onSuccess: openDownload,
  });
}
