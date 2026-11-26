import type { Metadata } from "next";

import { OrderHub } from "@/features/orders/components/order-hub";

export const metadata: Metadata = { title: "Pedido" };

export default async function OrderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <OrderHub id={id} />;
}
