import type { Schemas } from "@eumini/api-client";
import { env } from "@eumini/web-core/env";

export type Theme = Schemas["ThemeEnum"];

type ThemeInfo = {
  id: Theme;
  label: string;
  /** Miniatura de exemplo, no bucket público da plataforma. */
  image: string;
};

const image = (theme: Theme) => `${env.assetsUrl}/themes/${theme}-v1.webp`;

/** Temas do envio da foto, na ordem dos cards. O tema muda acessórios e roupa, não o preço. */
export const THEMES: ThemeInfo[] = [
  { id: "christmas", label: "Natal", image: image("christmas") },
  { id: "gta6", label: "GTA VI", image: image("gta6") },
];

/** Rótulo de um tema vindo da API ("" é sem tema). */
export function themeLabel(id: string): string {
  return THEMES.find((theme) => theme.id === id)?.label ?? "";
}
