import type { ReactNode } from "react";

import { Brand } from "@/components/layout/brand";

export default function AccessLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <>
      <header className="bg-accent shadow-card">
        <div className="mx-auto flex h-16 max-w-5xl items-center px-4 sm:px-6">
          <Brand href="/entrar" />
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-16 pt-6 sm:px-6">{children}</main>
    </>
  );
}
