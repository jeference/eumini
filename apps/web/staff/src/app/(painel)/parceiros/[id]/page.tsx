import type { Metadata } from "next";

import { PartnerDetail } from "@/features/partners/components/partner-detail";

export const metadata: Metadata = { title: "Parceiro" };

export default async function PartnerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PartnerDetail id={id} />;
}
