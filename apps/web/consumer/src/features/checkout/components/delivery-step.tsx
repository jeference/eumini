"use client";

import type { Schemas } from "@eumini/api-client";
import { Button } from "@eumini/ui/button";
import { TextField } from "@eumini/ui/form";
import { formatBRL, formatCep } from "@eumini/ui/lib/format";
import { RadioCard } from "@eumini/ui/radio-card";
import { Skeleton } from "@eumini/ui/skeleton";
import { MapPin } from "lucide-react";
import { useFormContext, useWatch } from "react-hook-form";

import type { CheckoutValues } from "@/features/checkout/schemas";

type Quote = Schemas["ShippingQuote"];

const CORREIOS_BUSCA_CEP = "https://buscacepinter.correios.com.br/app/endereco/index.php";

/** Rua, bairro, cidade e UF preenchidos: dá para mostrar o endereço como texto. */
export function hasFullAddress(
  values: Pick<CheckoutValues, "street" | "neighborhood" | "city" | "state">,
) {
  return (
    values.street.trim().length >= 2 &&
    values.neighborhood.trim().length >= 2 &&
    values.city.trim().length >= 2 &&
    /^[A-Za-z]{2}$/.test(values.state.trim())
  );
}

export function quoteLabel(quote: Quote) {
  return `${quote.company} ${quote.service_name}`;
}

export function DeliveryStep({
  cepComplete,
  lookupPending,
  editingAddress,
  onEditAddress,
  quotes,
  quotePending,
  quoteError,
  onRetryQuote,
  selectedQuoteId,
  onSelectQuote,
  shippingError,
}: {
  cepComplete: boolean;
  lookupPending: boolean;
  editingAddress: boolean;
  onEditAddress: () => void;
  quotes: Quote[];
  quotePending: boolean;
  quoteError: string | null;
  onRetryQuote: () => void;
  selectedQuoteId: string | null;
  onSelectQuote: (id: string) => void;
  shippingError: string | null;
}) {
  const { control } = useFormContext<CheckoutValues>();
  const [street, neighborhood, city, state] = useWatch({
    control,
    name: ["street", "neighborhood", "city", "state"],
  });
  const compact = !editingAddress && hasFullAddress({ street, neighborhood, city, state });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-x-4 gap-y-1.5">
        <TextField
          control={control}
          name="postal_code"
          label="CEP"
          inputMode="numeric"
          autoComplete="postal-code"
          format={formatCep}
          className="w-full sm:max-w-48"
        />
        <a
          href={CORREIOS_BUSCA_CEP}
          target="_blank"
          rel="noreferrer"
          className="pb-3 text-sm text-accent underline underline-offset-2"
        >
          Não sei meu CEP
        </a>
      </div>

      {cepComplete && lookupPending && <Skeleton className="h-28 w-full" />}

      {cepComplete && !lookupPending && (
        <div className="space-y-4">
          {compact ? (
            <div className="flex items-start gap-3 rounded-2xl border-2 border-stroke p-4">
              <MapPin aria-hidden className="mt-0.5 size-5 shrink-0 text-accent" />
              <p className="min-w-0 flex-1 text-sm">
                <span className="block font-semibold">{street}</span>
                <span className="block text-muted">
                  {neighborhood}, {city}/{state.toUpperCase()}
                </span>
              </p>
              <Button type="button" variant="secondary" size="sm" onClick={onEditAddress}>
                Editar
              </Button>
            </div>
          ) : (
            <>
              <TextField control={control} name="street" label="Rua" autoComplete="address-line1" />
              <TextField control={control} name="neighborhood" label="Bairro" />
              <div className="grid grid-cols-[minmax(0,1fr)_88px] gap-4">
                <TextField
                  control={control}
                  name="city"
                  label="Cidade"
                  autoComplete="address-level2"
                />
                <TextField
                  control={control}
                  name="state"
                  label="UF"
                  autoComplete="address-level1"
                  maxLength={2}
                />
              </div>
            </>
          )}
          <div className="grid grid-cols-[120px_minmax(0,1fr)] gap-4">
            <TextField control={control} name="number" label="Número" autoFocus={compact} />
            <TextField
              control={control}
              name="complement"
              label="Complemento (opcional)"
              placeholder="Apto, bloco, casa"
            />
          </div>
        </div>
      )}

      {cepComplete && (
        <fieldset className="space-y-3">
          <legend className="mb-3 text-sm font-semibold">Frete</legend>
          {quotePending && <Skeleton className="h-16 w-full" />}
          {quoteError && (
            <div className="flex flex-wrap items-center gap-3 text-sm text-danger" role="alert">
              {quoteError}
              <Button type="button" variant="secondary" size="sm" onClick={onRetryQuote}>
                Tentar de novo
              </Button>
            </div>
          )}
          {!quotePending &&
            quotes.map((option) => (
              <RadioCard
                key={option.id}
                name="shipping"
                checked={option.id === selectedQuoteId}
                onSelect={() => onSelectQuote(option.id)}
                aside={formatBRL(option.price_cents)}
              >
                <span className="block text-sm font-semibold">{quoteLabel(option)}</span>
                <span className="block text-xs text-muted">
                  Até {option.delivery_days} dias úteis, com a produção
                </span>
              </RadioCard>
            ))}
          {shippingError && !quoteError && (
            <p className="text-xs font-medium text-danger" role="alert">
              {shippingError}
            </p>
          )}
        </fieldset>
      )}
    </div>
  );
}
