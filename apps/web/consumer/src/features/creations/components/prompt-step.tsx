"use client";

import { Button } from "@eumini/ui/button";
import { formatBRL } from "@eumini/ui/lib/format";
import { cn } from "@eumini/ui/lib/utils";
import { RadioCard } from "@eumini/ui/radio-card";
import { CircleCheck, ImagePlus, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { type Category, categoryInfo } from "@/features/catalog/categories";
import { useProduct } from "@/features/catalog/hooks";
import { type Theme, THEMES } from "@/features/catalog/themes";
import { useStartCreation } from "@/features/creations/hooks";
import { messageOf } from "@/lib/errors";

const MAX_PHOTO_BYTES = 10 * 1024 * 1024;
// HEIC é o formato das fotos do iPhone; o servidor converte. Fora do Safari, um .heic costuma
// chegar sem tipo, então a extensão também vale.
const PHOTO_ACCEPT =
  "image/png,image/jpeg,image/webp,image/heic,image/heif,image/avif,.heic,.heif,.avif";
const PHOTO_TYPE = /^image\/(png|jpeg|webp|heic|heif|heic-sequence|heif-sequence|avif)$/;
const PHOTO_EXTENSION = /\.(png|jpe?g|webp|heic|heif|avif)$/i;

function isAcceptedPhoto(file: File) {
  if (file.type && file.type !== "application/octet-stream") return PHOTO_TYPE.test(file.type);
  return PHOTO_EXTENSION.test(file.name);
}

/** Envio da foto, a partir da página de uma categoria. */
export function PromptStep({ category }: { category: Category }) {
  const router = useRouter();
  const start = useStartCreation();
  const info = categoryInfo(category);
  const product = useProduct(category);
  const [theme, setTheme] = useState<Theme | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function submit() {
    if (!photo || start.isPending) return;
    start.mutate(
      { requestedCategory: category, theme, photo },
      {
        onSuccess: (creation) => router.push(`/criacoes/${creation.id}`),
        onError: (error) => toast.error(messageOf(error)),
      },
    );
  }

  function attachPhoto(file: File | undefined) {
    if (!file) return;
    if (!isAcceptedPhoto(file)) {
      const extension = file.name.includes(".") ? file.name.split(".").pop() : "sem extensão";
      toast.error(
        `Envie uma foto em JPG, PNG, WEBP, HEIC ou AVIF. Imagem enviada em ${extension} (${file.type || "sem tipo"}).`,
      );
      return;
    }
    if (file.size > MAX_PHOTO_BYTES) {
      toast.error("A foto deve ter no máximo 10 MB.");
      return;
    }
    setPhoto(file);
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-center font-display text-3xl font-semibold tracking-tight sm:text-4xl">
        {info.title}
      </h1>
      <p className="mt-2 text-center text-sm text-muted">
        Miniatura {info.label}
        {product?.from_price_cents
          ? ` a partir de ${formatBRL(product.from_price_cents)}`
          : ""}.{" "}
        <Link href="/#categorias" className="font-medium text-ink underline underline-offset-4">
          Trocar
        </Link>
      </p>

      <form
        className="mt-4 space-y-3 sm:mt-6"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <div
          className={cn(
            "relative rounded-3xl bg-sunken bg-[radial-gradient(rgb(var(--ink)/0.16)_1px,transparent_1px)] p-3 transition-colors [background-size:18px_18px]",
            isDragging && "bg-accent-soft ring-2 ring-accent",
          )}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
              setIsDragging(false);
            }
          }}
          onDrop={(event) => {
            event.preventDefault();
            setIsDragging(false);
            attachPhoto(event.dataTransfer.files[0]);
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept={PHOTO_ACCEPT}
            aria-label="Enviar foto"
            className="sr-only"
            onChange={(event) => {
              attachPhoto(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          <div className="flex justify-center py-2 sm:py-5">
            <PhotoPicker
              file={photo}
              onPick={() => fileInputRef.current?.click()}
              onRemove={() => setPhoto(null)}
            />
          </div>
          <ThemePicker noThemeImage={info.image} value={theme} onChange={setTheme} />

          {isDragging && (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <span className="rounded-full bg-surface px-4 py-2 text-sm font-medium shadow-card">
                Solte a foto aqui
              </span>
            </div>
          )}
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          disabled={!photo}
          pending={start.isPending}
          className="h-12 w-full text-base sm:h-14"
        >
          <Sparkles />
          Gerar
        </Button>
      </form>
    </div>
  );
}

/** Tema opcional, abaixo da foto. "Sem tema" mostra a miniatura da própria categoria. */
function ThemePicker({
  noThemeImage,
  value,
  onChange,
}: {
  noThemeImage: string;
  value: Theme | null;
  onChange: (theme: Theme | null) => void;
}) {
  const options = [{ id: null, label: "Sem tema", image: noThemeImage }, ...THEMES];
  return (
    <fieldset>
      <legend className="mb-2 text-center text-sm font-medium">Escolha um tema</legend>
      <div className="grid grid-cols-3 gap-2">
        {options.map((option) => (
          <RadioCard
            key={option.id ?? "none"}
            name="theme"
            checked={value === option.id}
            onSelect={() => onChange(option.id)}
            indicator={false}
            className="justify-center p-2 sm:p-2.5"
          >
            <span className="flex flex-col items-center gap-1.5">
              {/* eslint-disable-next-line @next/next/no-img-element -- miniatura do bucket público */}
              <img
                src={option.image}
                alt=""
                className="size-12 rounded-xl object-contain sm:size-16"
              />
              <span className="text-sm font-medium">{option.label}</span>
            </span>
          </RadioCard>
        ))}
      </div>
    </fieldset>
  );
}

function PhotoPicker({
  file,
  onPick,
  onRemove,
}: {
  file: File | null;
  onPick: () => void;
  onRemove: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  // Fora do Safari o navegador não desenha HEIC: no lugar da prévia, mostra que a foto foi anexada.
  const [previewFailed, setPreviewFailed] = useState(false);
  useEffect(() => {
    setPreviewFailed(false);
    if (!file) {
      setUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  return (
    // A altura da tela define o tamanho, para o formulário inteiro caber sem rolar até o Gerar.
    <div className="relative size-[clamp(5.5rem,calc(100svh-33rem),13rem)] sm:size-[clamp(5.5rem,calc(100svh-36rem),13rem)]">
      <button
        type="button"
        onClick={onPick}
        aria-label={file ? "Trocar foto" : "Enviar foto"}
        title="Criamos a imagem da miniatura a partir da sua foto"
        className="flex size-full flex-col items-center justify-center gap-3 overflow-hidden rounded-3xl border border-line bg-surface text-sm font-medium transition-colors hover:border-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        {url && !previewFailed ? (
          // eslint-disable-next-line @next/next/no-img-element -- prévia local do arquivo do cliente
          <img
            src={url}
            alt="Foto enviada"
            className="size-full object-cover"
            onError={() => setPreviewFailed(true)}
          />
        ) : file ? (
          <>
            <CircleCheck className="size-7 text-accent" aria-hidden />
            Foto anexada
            <span className="max-w-[85%] truncate text-xs font-normal text-muted">{file.name}</span>
          </>
        ) : (
          <>
            <ImagePlus className="size-7" aria-hidden />
            Envie sua foto
          </>
        )}
      </button>
      {file && (
        <Button
          variant="floating"
          size="icon-sm"
          onClick={onRemove}
          aria-label="Remover foto"
          className="absolute -right-2 -top-2"
        >
          <X aria-hidden />
        </Button>
      )}
    </div>
  );
}
