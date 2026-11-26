"use client";

import { Button } from "@eumini/ui/button";
import { Camera, X } from "lucide-react";
import { useEffect, useId, useMemo, useRef } from "react";

const ACCEPT = "image/jpeg,image/png,image/webp,image/heic,image/heif,image/avif";

/** Escolhe até `max` fotos, com prévia. HEIC sem prévia no navegador mostra só o nome. */
export function PhotoPicker({
  files,
  onChange,
  max,
  label = "Adicionar foto",
}: {
  files: File[];
  onChange: (files: File[]) => void;
  max: number;
  label?: string;
}) {
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const previews = useMemo(() => files.map((file) => URL.createObjectURL(file)), [files]);

  useEffect(() => () => previews.forEach((url) => URL.revokeObjectURL(url)), [previews]);

  function add(list: FileList | null) {
    if (!list) return;
    onChange([...files, ...Array.from(list)].slice(0, max));
    if (input.current) input.current.value = "";
  }

  return (
    <div>
      {files.length > 0 && (
        <ul className="mb-3 flex flex-wrap gap-2">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element -- prévia local */}
              <img
                src={previews[index]}
                alt={file.name}
                className="size-20 rounded-xl bg-sunken object-cover"
              />
              <button
                type="button"
                aria-label={`Remover ${file.name}`}
                onClick={() => onChange(files.filter((_, i) => i !== index))}
                className="absolute -right-1.5 -top-1.5 flex size-6 items-center justify-center rounded-full bg-ink text-white"
              >
                <X className="size-3.5" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
      {files.length < max && (
        <>
          <input
            ref={input}
            id={inputId}
            type="file"
            accept={ACCEPT}
            multiple={max > 1}
            className="sr-only"
            onChange={(event) => add(event.target.files)}
          />
          <Button asChild variant="secondary">
            <label htmlFor={inputId} className="cursor-pointer">
              <Camera aria-hidden />
              {label}
            </label>
          </Button>
        </>
      )}
    </div>
  );
}
