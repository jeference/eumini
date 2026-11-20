"use client";

import { Button } from "@kubo/ui/button";
import { Callout } from "@kubo/ui/callout";
import { Checkbox } from "@kubo/ui/checkbox";
import { Input } from "@kubo/ui/input";
import { Label } from "@kubo/ui/label";
import { ImagePlus, Scissors } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import {
  GROUP_REASONS,
  REJECTION_MESSAGES,
  type RejectionReason,
  categoryInfo,
} from "@/features/catalog/categories";
import { useJoinWaitlist } from "@/features/creations/hooks";
import type { Creation } from "@/features/creations/types";
import { messageOf } from "@/lib/errors";

function reasonOf(creation: Creation): RejectionReason | null {
  return creation.rejection_reason || null;
}

export function isGroupRejection(creation: Creation): boolean {
  const reason = reasonOf(creation);
  return reason !== null && GROUP_REASONS.has(reason);
}

/** Dentro do quadro da imagem: o motivo e o caminho para outra foto. Nada foi gerado. */
export function RejectionMessage({ creation }: { creation: Creation }) {
  const reason = reasonOf(creation);
  const group = isGroupRejection(creation);
  const retryHref = `/criar/${categoryInfo(creation.requested_category).slug}`;
  return (
    <div
      className="flex size-full flex-col items-center justify-center gap-4 p-8 text-center"
      role="alert"
    >
      <p className="font-display text-xl font-semibold">
        {group ? "Recorte e nós fazemos" : "Precisamos de uma pessoa ou um pet na foto"}
      </p>
      <p className="text-sm text-muted">
        {reason ? REJECTION_MESSAGES[reason] : "Não conseguimos usar esta foto."}{" "}
        {group
          ? "Fazemos uma pessoa, um pet, um casal ou uma pessoa com seu pet. Recorte a foto para deixar só quem vai na miniatura."
          : "Envie outra foto, com uma pessoa, um pet, um casal ou uma pessoa com seu pet."}
      </p>
      <Button asChild variant="primary">
        <Link href={retryHref}>
          {group ? <Scissors aria-hidden /> : <ImagePlus aria-hidden />}
          {group ? "Enviar foto recortada" : "Escolher outra foto"}
        </Link>
      </Button>
      <p className="text-xs text-muted">A foto recusada não conta no seu limite de imagens.</p>
    </div>
  );
}

/** Para fotos com gente ou pets demais: avisamos quando essa miniatura existir (RN-37). */
export function WaitlistForm({ creation }: { creation: Creation }) {
  const join = useJoinWaitlist();
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [joined, setJoined] = useState(false);

  if (joined) {
    return (
      <Callout tone="accent" role="status">
        Pronto. Avisamos no seu e-mail quando fizermos miniaturas com mais pessoas ou pets.
      </Callout>
    );
  }

  return (
    <form
      className="space-y-4 lg:animate-fade-in"
      onSubmit={(event) => {
        event.preventDefault();
        if (!consent || !email.trim()) return;
        join.mutate(
          { creation_id: creation.id, email: email.trim(), consent },
          {
            onSuccess: () => setJoined(true),
            onError: (error) => toast.error(messageOf(error)),
          },
        );
      }}
    >
      <div className="space-y-2">
        <h2 className="font-display text-2xl font-semibold tracking-tight">
          Me avise quando estiver pronto
        </h2>
        <p className="text-sm text-muted">
          Ainda não fazemos miniaturas com mais pessoas ou pets. Deixe seu e-mail e avisamos quando
          fizermos.
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="waitlist-email">E-mail</Label>
        <Input
          id="waitlist-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </div>
      <Checkbox checked={consent} onChange={(event) => setConsent(event.target.checked)}>
        Quero receber um e-mail da Kubo só para avisar quando essa miniatura existir.
      </Checkbox>
      <Button type="submit" disabled={!consent || !email.trim()} pending={join.isPending}>
        Me avise
      </Button>
    </form>
  );
}
