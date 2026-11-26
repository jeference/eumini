"use client";

import { ApiClientProvider, createQueryClient } from "@eumini/api-client/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, useState } from "react";

import { getApiClient } from "./api";
import { SessionBootstrap } from "./components/session-bootstrap";
import type { SessionMode } from "./session";

/** Núcleo comum aos apps web. Cada app compõe por cima o que é seu. */
export function CoreProviders({
  children,
  mode = "visitor",
}: Readonly<{ children: ReactNode; mode?: SessionMode }>) {
  const [queryClient] = useState(() => createQueryClient());
  const [apiClient] = useState(() => getApiClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ApiClientProvider client={apiClient}>
        <SessionBootstrap mode={mode} />
        {children}
      </ApiClientProvider>
    </QueryClientProvider>
  );
}
