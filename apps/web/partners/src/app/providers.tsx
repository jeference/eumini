"use client";

import { Toaster } from "@eumini/ui/sonner";
import { CoreProviders } from "@eumini/web-core/providers";
import type { ReactNode } from "react";

/** Só contas: o app de parceiros não tem visitante. */
export function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <CoreProviders mode="account">
      {children}
      <Toaster />
    </CoreProviders>
  );
}
