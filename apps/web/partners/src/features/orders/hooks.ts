"use client";

import { type Schemas, unwrap } from "@eumini/api-client";
import { qk, useApiClient } from "@eumini/api-client/react";
import { useSession } from "@eumini/web-core/session";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { stableUrl } from "@/lib/stable-url";

export type PartnerOrder = Schemas["PartnerOrderDetail"];
export type PartnerOrderRow = Schemas["PartnerOrderList"];
export type OrderGroup = Schemas["PartnerOrderGroupEnum"];

/** A fila e o detalhe se atualizam sozinhos: a etiqueta e os cancelamentos chegam da EuMini. */
const POLL_MS = 30_000;

function useAuthenticated(): boolean {
  return useSession((state) => state.status === "authenticated");
}

function withStableUrls(order: PartnerOrder): PartnerOrder {
  return {
    ...order,
    thumbnail_url: stableUrl(`thumb:${order.id}`, order.thumbnail_url),
    items: order.items.map((item) => ({
      ...item,
      image_url: stableUrl(`item:${item.id}`, item.image_url),
    })),
    photos: order.photos.map((photo) => ({ ...photo, url: stableUrl(photo.id, photo.url) })),
    issues: order.issues.map((issue) => ({
      ...issue,
      photo_url: stableUrl(`issue:${issue.id}`, issue.photo_url),
    })),
  };
}

export function useOrderSummary() {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.partnerSummary(),
    enabled: useAuthenticated(),
    refetchInterval: POLL_MS,
    queryFn: async () => unwrap(await api.GET("/api/partner/orders/summary/")),
  });
}

export function useOrders(group: OrderGroup) {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.partnerOrders(group),
    enabled: useAuthenticated(),
    refetchInterval: POLL_MS,
    queryFn: async () =>
      unwrap(await api.GET("/api/partner/orders/", { params: { query: { group } } })),
    select: (page) => ({
      ...page,
      results: page.results.map((row) => ({
        ...row,
        thumbnail_url: stableUrl(`thumb:${row.id}`, row.thumbnail_url),
      })),
    }),
  });
}

export function useOrder(id: string) {
  const api = useApiClient();
  return useQuery({
    queryKey: qk.partnerOrder(id),
    enabled: useAuthenticated(),
    refetchInterval: POLL_MS,
    staleTime: 0,
    queryFn: async () =>
      unwrap(
        await api.GET("/api/partner/orders/{order_id}/", {
          params: { path: { order_id: id } },
        }),
      ),
    select: withStableUrls,
  });
}

/** Ações do pedido. Cada uma devolve o pedido atualizado e invalida a fila. */
export function useOrderActions(id: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();
  const path = { params: { path: { order_id: id } } };

  function settle(order?: PartnerOrder) {
    if (order) queryClient.setQueryData(qk.partnerOrder(id), order);
    void queryClient.invalidateQueries({ queryKey: qk.partner() });
  }

  const start = useMutation({
    mutationFn: async () => unwrap(await api.POST("/api/partner/orders/{order_id}/start/", path)),
    onSuccess: settle,
  });
  const post = useMutation({
    mutationFn: async () => unwrap(await api.POST("/api/partner/orders/{order_id}/post/", path)),
    onSuccess: settle,
  });
  const refuse = useMutation({
    mutationFn: async (reason: string) => {
      unwrap(
        await api.POST("/api/partner/orders/{order_id}/refuse/", { ...path, body: { reason } }),
      );
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: qk.partner() }),
  });
  const ready = useMutation({
    mutationFn: async (photos: File[]) => {
      const form = new FormData();
      for (const photo of photos) form.append("photos", photo);
      return unwrap(
        await api.POST("/api/partner/orders/{order_id}/ready/", {
          ...path,
          body: form as never,
          bodySerializer: (body) => body as unknown as FormData,
        }),
      );
    },
    onSuccess: settle,
  });
  const reportIssue = useMutation({
    mutationFn: async (input: { text: string; photo?: File | null }) => {
      const form = new FormData();
      form.set("text", input.text);
      if (input.photo) form.set("photo", input.photo);
      return unwrap(
        await api.POST("/api/partner/orders/{order_id}/issues/", {
          ...path,
          body: form as never,
          bodySerializer: (body) => body as unknown as FormData,
        }),
      );
    },
    onSuccess: settle,
  });

  return { start, post, refuse, ready, reportIssue };
}

/** Pede a URL assinada (o download fica registrado) e abre o arquivo. */
export function useDownload(orderId: string) {
  const api = useApiClient();
  return useMutation({
    mutationFn: async (
      target: { kind: "item"; itemId: string; file: "3mf" | "image" } | { kind: "label" },
    ) => {
      if (target.kind === "label") {
        return unwrap(
          await api.POST("/api/partner/orders/{order_id}/label/download/", {
            params: { path: { order_id: orderId } },
          }),
        );
      }
      return unwrap(
        await api.POST("/api/partner/orders/{order_id}/items/{item_id}/download/", {
          params: { path: { order_id: orderId, item_id: target.itemId } },
          body: { file: target.file },
        }),
      );
    },
    onSuccess: ({ url, filename }) => {
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.rel = "noopener";
      document.body.appendChild(link);
      link.click();
      link.remove();
    },
  });
}
