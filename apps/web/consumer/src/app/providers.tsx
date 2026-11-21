"use client";

import { Toaster } from "@eumini/ui/sonner";
import { CoreProviders } from "@eumini/web-core/providers";
import type { ReactNode } from "react";

export function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <CoreProviders>
      {children}
      <Toaster />
    </CoreProviders>
  );
}
