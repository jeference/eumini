import type { ReactNode } from "react";

import { AppHeader } from "@/components/layout/app-header";
import { StaffGuard } from "@/components/layout/staff-guard";

export default function PanelLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <>
      <AppHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-16 pt-6 sm:px-6">
        <StaffGuard>{children}</StaffGuard>
      </main>
    </>
  );
}
