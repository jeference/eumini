"use client";

import { track } from "@kubo/analytics";
import { Button } from "@kubo/ui/button";
import { Callout } from "@kubo/ui/callout";
import { Chip, ChipGroup } from "@kubo/ui/chip";
import { formatBRL } from "@kubo/ui/lib/format";
import { QuantityStepper } from "@kubo/ui/quantity-stepper";
import { ShoppingBag, ShoppingCart } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { useAddToCart } from "@/features/cart/hooks";
import { REJECTION_MESSAGES, categoryInfo } from "@/features/catalog/categories";
import { useProduct } from "@/features/catalog/hooks";
import type { Creation } from "@/features/creations/types";
import { messageOf } from "@/lib/errors";

const MAX_QUANTITY = 10;

export function PurchasePanel({ creation }: { creation: Creation }) {
  const router = useRouter();
  // O preço vem da categoria da imagem atual, não da página de entrada (RN-34).
  const version = creation.versions.find((v) => v.id === creation.current_version_id);
  const product = useProduct(version?.category);
  const sizes = product?.sizes ?? [];
  const add = useAddToCart();
  const [chosenId, setChosenId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [buying, setBuying] = useState(false);

  const size =
    sizes.find((option) => option.id === chosenId) ??
    sizes.find((option) => option.is_default) ??
    sizes[0];

  if (version?.rejection_reason) {
    return (
      <Callout tone="danger" role="alert">
        Esta imagem não pode ser comprada. {REJECTION_MESSAGES[version.rejection_reason]} Edite a
        imagem ou escolha outra versão.
      </Callout>
    );
  }

  function addToCart(buyNow: boolean) {
    if (!size) return;
    setBuying(buyNow);
    track(buyNow ? "buy_now_clicked" : "item_added_to_cart", { size: size.code, quantity });
    add.mutate(
      { creation_id: creation.id, size_id: size.id, quantity },
      {
        onSuccess: (item) => {
          if (buyNow) {
            router.push(`/checkout?item=${item.id}`);
            return;
          }
          toast.success("Adicionado ao carrinho.", {
            action: { label: "Ver carrinho", onClick: () => router.push("/carrinho") },
          });
        },
        onError: (error) => toast.error(messageOf(error)),
      },
    );
  }

  return (
    // Sem animação no celular: o transform moveria os botões fixos enquanto roda.
    <div className="space-y-6 pb-10 lg:animate-fade-in lg:pb-0">
      <div>
        {version?.category && (
          <p className="mb-3 text-sm font-medium text-muted">
            Miniatura {categoryInfo(version.category).label}
          </p>
        )}
        <p className="text-3xl font-semibold" data-testid="price">
          {size ? formatBRL(size.price_cents * quantity) : "…"}
        </p>
        <p className="mt-2 text-sm text-muted lg:text-[13px]">Frete calculado na finalização</p>
      </div>

      <ChipGroup label="Tamanho">
        {sizes.map((option) => (
          <Chip
            key={option.id}
            selected={option.id === size?.id}
            onClick={() => {
              setChosenId(option.id);
              track("size_selected", { size: option.code });
            }}
          >
            {option.label}
          </Chip>
        ))}
      </ChipGroup>

      <div>
        <p className="text-sm font-semibold">Quantidade</p>
        <QuantityStepper
          className="mt-2.5"
          value={quantity}
          max={MAX_QUANTITY}
          onChange={setQuantity}
        />
      </div>

      <Callout className="text-[13px]">
        A imagem é uma prévia. A peça é impressa em filamento com até 4 cores, então forma, cores e
        detalhes podem ser diferentes.
      </Callout>

      {/* Fixos no rodapé do celular. */}
      <div className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-2 gap-3 border-t border-line bg-background p-4 lg:static lg:border-0 lg:bg-transparent lg:p-0">
        <Button
          size="lg"
          className="whitespace-normal px-3 text-sm leading-tight lg:px-7"
          disabled={!size}
          pending={add.isPending && !buying}
          onClick={() => addToCart(false)}
        >
          <ShoppingCart aria-hidden />
          Adicionar ao carrinho
        </Button>
        <Button
          variant="primary"
          size="lg"
          className="whitespace-normal px-3 text-sm leading-tight lg:px-7"
          disabled={!size}
          pending={add.isPending && buying}
          onClick={() => addToCart(true)}
        >
          <ShoppingBag aria-hidden />
          Comprar agora
        </Button>
      </div>
    </div>
  );
}
