"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { track } from "@kubo/analytics";
import { ApiError, type Schemas, unwrap } from "@kubo/api-client";
import { qk, useApiClient } from "@kubo/api-client/react";
import { Button } from "@kubo/ui/button";
import { Callout } from "@kubo/ui/callout";
import { EmptyState } from "@kubo/ui/empty-state";
import { Form } from "@kubo/ui/form";
import { formatBRL, formatCep } from "@kubo/ui/lib/format";
import { Skeleton } from "@kubo/ui/skeleton";
import { Steps } from "@kubo/ui/steps";
import { useSession } from "@kubo/web-core/session";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { useCart } from "@/features/cart/hooks";
import {
  CHECKOUT_FORM_ID,
  CheckoutAction,
  CheckoutStep,
  STEP_HEADING_ID,
} from "@/features/checkout/components/checkout-step";
import {
  CheckoutSummaryBar,
  CheckoutSummaryPanel,
} from "@/features/checkout/components/checkout-summary";
import { ContactStep } from "@/features/checkout/components/contact-step";
import { DeliveryStep } from "@/features/checkout/components/delivery-step";

import { PaymentMethodPicker, TermsCheckbox } from "@/features/checkout/components/payment-method";
import { PixModal } from "@/features/checkout/components/pix-modal";
import {
  type CheckoutValues,
  checkoutSchema,
  firstIncompleteStep,
  type FormStep,
  STEP_FIELDS,
  type Step,
  STEPS,
  stepOfField,
} from "@/features/checkout/schemas";
import { messageOf } from "@/lib/errors";

type Quote = Schemas["ShippingQuote"];

/** Título do cartão de cada etapa. O Pagar tem o próprio ("Forma de pagamento"). */
const STEP_LABELS: Record<Exclude<Step, "pagar">, string> = {
  dados: "Seus dados",
  entrega: "Entrega",
};
/** Rótulos curtos da trilha. */
const TRAIL_LABELS: Record<Step, string> = {
  dados: "Dados",
  entrega: "Endereço",
  pagar: "Pagamento",
};
const STEP_ITEMS = STEPS.map((id) => ({ id, label: TRAIL_LABELS[id] }));
const ADDRESS_FIELDS = ["street", "neighborhood", "city", "state"] as const;

const indexOf = (step: Step) => STEPS.indexOf(step);
const isStep = (value: string | null): value is Step => STEPS.includes(value as Step);

export function CheckoutForm() {
  const api = useApiClient();
  const router = useRouter();
  const queryClient = useQueryClient();
  const params = useSearchParams();
  const onlyItem = params.get("item");
  const user = useSession((state) => state.user);
  const { data: cart, isLoading } = useCart();

  const form = useForm<CheckoutValues>({
    resolver: zodResolver(checkoutSchema),
    mode: "onTouched",
    defaultValues: {
      email: "",
      name: "",
      cpf: "",
      postal_code: "",
      street: "",
      number: "",
      complement: "",
      neighborhood: "",
      city: "",
      state: "",
    },
  });

  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [selectedQuoteId, setSelectedQuoteId] = useState<string | null>(null);
  const [shippingNotice, setShippingNotice] = useState<string | null>(null);
  const [shippingError, setShippingError] = useState<string | null>(null);
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [termsError, setTermsError] = useState(false);
  const [lookupPending, setLookupPending] = useState(false);
  const [editingAddress, setEditingAddress] = useState(false);
  // CEP a que rua, bairro, cidade e UF pertencem: evita buscar de novo o que já veio salvo.
  const addressCep = useRef<string | null>(null);
  // A mesma chave em toda tentativa: um clique duplo nunca cria dois pedidos.
  const idempotencyKey = useRef(crypto.randomUUID());
  // Forma de pagamento: nada vem marcado.
  const [pixChosen, setPixChosen] = useState(false);
  const [methodError, setMethodError] = useState(false);
  // Pedido criado no "Concluir pagamento". O PIX aparece num modal por cima do Pagar.
  const [orderId, setOrderId] = useState<string | null>(null);
  const [pixOpen, setPixOpen] = useState(false);

  // A etapa mora na URL para o voltar do navegador voltar uma etapa. Nunca passa da
  // mais avançada já liberada (recarregar a página recomeça do início).
  const [reached, setReached] = useState<Step>("dados");
  const requested = params.get("etapa");
  const wanted: Step = isStep(requested) ? requested : "dados";
  const step: Step = indexOf(wanted) <= indexOf(reached) ? wanted : reached;

  // Saiu do Pagar depois de criar o pedido: os dados podem mudar, então o próximo
  // "Concluir pagamento" cria outro pedido (chave nova). O anterior expira sozinho.
  useEffect(() => {
    if (step !== "pagar" && orderId) {
      setOrderId(null);
      setPixOpen(false);
      idempotencyKey.current = crypto.randomUUID();
    }
  }, [step, orderId]);

  const items = (cart?.items ?? []).filter(
    (item) => !item.unavailable_reason && (!onlyItem || item.id === onlyItem),
  );
  const itemIds = items.map((item) => item.id);
  const itemKey = itemIds.join(",");
  const subtotal = items.reduce((total, item) => total + item.line_total_cents, 0);
  const selectedQuote = quotes.find((quote) => quote.id === selectedQuoteId) ?? null;

  function stepUrl(next: Step) {
    const search = new URLSearchParams(params.toString());
    if (next === "dados") search.delete("etapa");
    else search.set("etapa", next);
    const query = search.toString();
    return query ? `/checkout?${query}` : "/checkout";
  }

  function goTo(next: Step) {
    router.push(stepUrl(next), { scroll: false });
  }

  // Trocou de etapa (botão, indicador ou voltar do navegador): foco no título da nova
  // etapa e, se ele ficou acima da tela, volta ao topo. No primeiro render não mexe.
  const shownStep = useRef(step);
  useEffect(() => {
    if (shownStep.current === step) return;
    shownStep.current = step;
    const heading = document.getElementById(STEP_HEADING_ID);
    heading?.focus({ preventScroll: true });
    if (heading && heading.getBoundingClientRect().top < 0) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [step]);

  // URL pedindo uma etapa ainda não liberada: corrige sem criar entrada no histórico.
  useEffect(() => {
    if (wanted !== step) router.replace(stepUrl(step), { scroll: false });
    // stepUrl muda a cada render; o que importa é a etapa.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wanted, step]);

  const { data: addresses } = useQuery({
    queryKey: qk.addresses(),
    enabled: Boolean(user),
    queryFn: async () => unwrap(await api.GET("/api/me/addresses/")),
  });

  // Conta: preenche o que já sabemos, sem apagar o que foi digitado.
  useEffect(() => {
    if (!user) return;
    const current = form.getValues();
    if (!current.email) form.setValue("email", user.email);
    if (!current.name && user.first_name) form.setValue("name", user.first_name);
  }, [user, form]);

  useEffect(() => {
    const saved = addresses?.[0];
    if (!saved || form.getValues("postal_code")) return;
    addressCep.current = saved.postal_code.replace(/\D/g, "");
    form.reset({
      ...form.getValues(),
      postal_code: formatCep(saved.postal_code),
      street: saved.street,
      number: saved.number,
      complement: saved.complement,
      neighborhood: saved.neighborhood,
      city: saved.city,
      state: saved.state,
    });
  }, [addresses, form]);

  useEffect(() => {
    if (itemKey) track("checkout_started", { items: itemIds.length });
    // Só uma vez por conjunto de itens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemKey]);

  const postalCode = form.watch("postal_code");
  const cepDigits = postalCode.replace(/\D/g, "");

  const quote = useMutation({
    mutationFn: async (variables: { postalCode: string; itemIds: string[] }) =>
      unwrap(
        await api.POST("/api/shipping/quotes/", {
          body: { postal_code: variables.postalCode, item_ids: variables.itemIds },
        }),
      ),
    onSuccess: (result) => {
      setQuotes(result);
      setSelectedQuoteId(result[0]?.id ?? null);
      setQuoteError(null);
      track("shipping_quoted", { options: result.length });
    },
    onError: (error) => {
      setQuotes([]);
      setSelectedQuoteId(null);
      setQuoteError(messageOf(error, "Não conseguimos calcular o frete. Tente de novo."));
    },
  });
  const quoteMutate = quote.mutate;

  // CEP completo: cota o frete e, se o endereço ainda não é desse CEP, busca o endereço.
  useEffect(() => {
    setShippingNotice(null);
    setShippingError(null);
    if (cepDigits.length !== 8 || !itemKey) {
      setQuotes([]);
      setSelectedQuoteId(null);
      setQuoteError(null);
      setLookupPending(false);
      return;
    }
    quoteMutate({ postalCode: cepDigits, itemIds: itemKey.split(",") });
    if (addressCep.current === cepDigits) return;

    let cancelled = false;
    setLookupPending(true);
    void (async () => {
      let data: Schemas["AddressLookup"] | undefined;
      try {
        ({ data } = await api.GET("/api/shipping/address/{postal_code}/", {
          params: { path: { postal_code: cepDigits } },
        }));
      } catch {
        data = undefined;
      }
      if (cancelled) return;
      // Endereço de outro CEP não serve: troca tudo, e o que faltar o cliente digita.
      addressCep.current = cepDigits;
      form.setValue("street", data?.street || "");
      form.setValue("neighborhood", data?.neighborhood || "");
      form.setValue("city", data?.city || "");
      form.setValue("state", data?.state || "");
      form.clearErrors([...ADDRESS_FIELDS]);
      setEditingAddress(false);
      setLookupPending(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [cepDigits, itemKey, api, form, quoteMutate]);

  // "Concluir pagamento" no Pix: cria o pedido e já gera o PIX. Se o PIX falhar, o modal
  // tenta de novo sozinho e oferece "Tentar de novo".
  const placeOrder = useMutation({
    mutationFn: async (values: CheckoutValues) => {
      const order = unwrap(
        await api.POST("/api/orders/", {
          params: { header: { "Idempotency-Key": idempotencyKey.current } },
          body: {
            ...values,
            complement: values.complement ?? "",
            item_ids: itemIds,
            shipping_quote_id: selectedQuoteId ?? "",
            accept_terms: acceptTerms,
          },
        }),
      );
      const charged = await api.POST("/api/orders/{order_id}/pay/", {
        params: { path: { order_id: order.id } },
      });
      if (charged.data) {
        track("pix_generated");
        queryClient.setQueryData(qk.order(order.id), charged.data);
      }
      return order;
    },
    onSuccess: (order) => {
      void queryClient.invalidateQueries({ queryKey: qk.orders() });
      setOrderId(order.id);
      setPixOpen(true);
    },
    onError: (error) => {
      if (error instanceof ApiError && error.code === "shipping_changed") {
        const raw = error.raw as {
          new_quote_id?: string;
          new_price_cents?: number;
          new_delivery_days?: number;
        };
        if (raw.new_quote_id && raw.new_price_cents !== undefined) {
          const previous = selectedQuote;
          const updated: Quote = {
            ...(previous as Quote),
            id: raw.new_quote_id,
            price_cents: raw.new_price_cents,
            delivery_days: raw.new_delivery_days ?? previous?.delivery_days ?? 0,
          };
          setQuotes([updated]);
          setSelectedQuoteId(updated.id);
          setShippingNotice(
            `O frete mudou para ${formatBRL(raw.new_price_cents)}. Confira o total e confirme.`,
          );
          return;
        }
        quoteMutate({ postalCode: cepDigits, itemIds });
        setShippingNotice(error.message);
        return;
      }
      if (error instanceof ApiError && error.fieldErrors) {
        // Leva o cliente à primeira etapa com campo recusado.
        let target: Step | null = null;
        for (const [field, messages] of Object.entries(error.fieldErrors)) {
          form.setError(field as keyof CheckoutValues, { message: messages[0] });
          const owner = stepOfField(field);
          if (owner && (!target || indexOf(owner) < indexOf(target))) target = owner;
          if ((ADDRESS_FIELDS as readonly string[]).includes(field)) setEditingAddress(true);
        }
        if (target) goTo(target);
      }
      toast.error(messageOf(error));
    },
  });

  // Voltou do Pagar para alterar algo: ao continuar, segue direto para o Pagar,
  // a menos que outra etapa tenha ficado pendente.
  function complete(done: FormStep, next: Step) {
    track("checkout_step_completed", { step: done });
    if (reached === "pagar") {
      const pending = firstIncompleteStep(form.getValues());
      goTo(pending === "pagar" && !selectedQuote ? "entrega" : pending);
      return;
    }
    if (indexOf(next) > indexOf(reached)) setReached(next);
    goTo(next);
  }

  async function advance() {
    if (step === "dados") {
      if (await form.trigger([...STEP_FIELDS.dados], { shouldFocus: true })) {
        complete("dados", "entrega");
      }
      return;
    }
    if (cepDigits.length !== 8 || lookupPending) {
      await form.trigger("postal_code", { shouldFocus: true });
      return;
    }
    if (!(await form.trigger([...STEP_FIELDS.entrega], { shouldFocus: true }))) return;
    if (!selectedQuote) {
      setShippingError(
        quote.isPending ? "Aguarde o cálculo do frete." : "Escolha uma opção de frete.",
      );
      return;
    }
    complete("entrega", "pagar");
  }

  function pay() {
    if (!pixChosen) {
      setMethodError(true);
      return;
    }
    if (!selectedQuote) {
      goTo("entrega");
      return;
    }
    if (!acceptTerms) {
      setTermsError(true);
      return;
    }
    // Já criou o pedido e voltou do modal: reabre o mesmo PIX.
    if (orderId) {
      setPixOpen(true);
      return;
    }
    void form.handleSubmit(
      (values) => placeOrder.mutate(values),
      () => goTo(firstIncompleteStep(form.getValues())),
    )();
  }

  if (isLoading || !cart) {
    return (
      <div className="mx-auto max-w-5xl space-y-3">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }
  // Com pedido criado, o carrinho pode esvaziar ao pagar: segue na tela até ir ao pedido.
  if (items.length === 0 && !orderId) {
    return (
      <div className="mx-auto max-w-xl py-8">
        <EmptyState
          title="Nada para finalizar"
          description="Seu carrinho está vazio, ou os itens não estão mais disponíveis."
          action={
            <Button asChild variant="primary">
              <Link href="/carrinho">Ver carrinho</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const shippingCents = selectedQuote?.price_cents ?? null;
  const next = onlyItem ? `/checkout?item=${onlyItem}` : "/checkout";

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="font-display text-3xl font-semibold tracking-tight">Finalizar compra</h1>
      {!user && (
        <p className="mt-2 text-sm text-muted">
          Não precisa de conta: enviamos o acompanhamento para o seu e-mail.{" "}
          <Link href={`/entrar?next=${encodeURIComponent(next)}`} className="text-accent underline">
            Já tenho conta
          </Link>
        </p>
      )}

      <Steps steps={STEP_ITEMS} current={step} onSelect={goTo} className="mt-6 max-w-xl" />

      <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px] lg:gap-8">
        <div className="space-y-4">
          <CheckoutSummaryBar items={items} subtotal={subtotal} shippingCents={shippingCents} />
          <Form {...form}>
            <form
              id={CHECKOUT_FORM_ID}
              noValidate
              onSubmit={(event) => {
                event.preventDefault();
                if (step === "pagar") pay();
                else void advance();
              }}
              className="space-y-4"
            >
              {step === "pagar" ? (
                <PaymentMethodPicker
                  pixChosen={pixChosen}
                  onChoosePix={() => {
                    setPixChosen(true);
                    setMethodError(false);
                  }}
                  error={methodError}
                >
                  {shippingNotice && (
                    <Callout tone="accent" role="alert">
                      {shippingNotice}
                    </Callout>
                  )}
                  <TermsCheckbox
                    checked={acceptTerms}
                    onChange={(checked) => {
                      setAcceptTerms(checked);
                      if (checked) setTermsError(false);
                    }}
                    error={termsError}
                  />
                </PaymentMethodPicker>
              ) : (
                <CheckoutStep title={STEP_LABELS[step]}>
                  {step === "dados" && <ContactStep />}
                  {step === "entrega" && (
                    <DeliveryStep
                      cepComplete={cepDigits.length === 8}
                      lookupPending={lookupPending}
                      editingAddress={editingAddress}
                      onEditAddress={() => setEditingAddress(true)}
                      quotes={quotes}
                      quotePending={quote.isPending}
                      quoteError={quoteError}
                      onRetryQuote={() => quoteMutate({ postalCode: cepDigits, itemIds })}
                      selectedQuoteId={selectedQuoteId}
                      onSelectQuote={(id) => {
                        setSelectedQuoteId(id);
                        setShippingError(null);
                      }}
                      shippingError={shippingError}
                    />
                  )}
                </CheckoutStep>
              )}
            </form>
          </Form>
        </div>
        <div className="h-fit space-y-4 lg:sticky lg:top-6">
          <CheckoutSummaryPanel items={items} subtotal={subtotal} shippingCents={shippingCents} />
          <CheckoutAction finish={step === "pagar"} pending={placeOrder.isPending} />
        </div>
      </div>

      {orderId && <PixModal orderId={orderId} open={pixOpen} onClose={() => setPixOpen(false)} />}
    </div>
  );
}
