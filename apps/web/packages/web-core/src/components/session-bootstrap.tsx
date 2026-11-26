"use client";

import { unwrap } from "@eumini/api-client";
import { useApiClient } from "@eumini/api-client/react";
import { useEffect } from "react";

import { refreshSession } from "../api";
import { type SessionMode, useSession } from "../session";

/**
 * Ao carregar: tenta restaurar a conta pelo cookie de refresh e, no modo `visitor`, garante o
 * cookie de visitante. Não renderiza nada. Só decide se quem está aqui é conta ou visitante.
 */
export function SessionBootstrap({ mode = "visitor" }: { mode?: SessionMode }) {
  const api = useApiClient();

  useEffect(() => {
    let active = true;
    useSession.getState().setMode(mode);

    if (mode === "visitor") {
      void fetch("/bff/visitor", { method: "POST" })
        .catch(() => undefined)
        .finally(() => {
          if (active) useSession.getState().setVisitorReady();
        });
    }

    void (async () => {
      const token = await refreshSession();
      if (!token) {
        if (active) useSession.getState().setAnonymous();
        return;
      }
      try {
        const me = unwrap(await api.GET("/api/me/"));
        if (active) useSession.getState().setSession(token, me);
      } catch {
        if (active) useSession.getState().setAnonymous();
      }
    })();

    return () => {
      active = false;
    };
  }, [api, mode]);

  return null;
}
