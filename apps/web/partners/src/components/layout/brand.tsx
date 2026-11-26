import Link from "next/link";

/** Marca EuMini com o selo "Parceiros", no mesmo desenho do app do cliente. */
export function Brand({ href = "/impressoes" }: { href?: string }) {
  return (
    <Link href={href} aria-label="EuMini Parceiros" className="flex items-center gap-2">
      <span className="flex items-center text-xl lg:text-2xl">
        <picture className="shrink-0">
          <source srcSet="/brand/eumini-cube-still.webp" media="(prefers-reduced-motion: reduce)" />
          <img
            src="/brand/eumini-cube.webp"
            alt=""
            width={72}
            height={72}
            className="size-[1.2em]"
          />
        </picture>
        {/* eslint-disable-next-line @next/next/no-img-element -- tamanho em em, junto com o cubo */}
        <img
          src="/brand/eumini-word.webp"
          alt=""
          width={157}
          height={144}
          className="h-[0.85em] w-auto translate-y-[0.18em]"
        />
      </span>
      <span className="rounded-full bg-highlight px-2.5 py-0.5 text-xs font-semibold text-ink">
        Parceiros
      </span>
    </Link>
  );
}
