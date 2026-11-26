"use client";

import { cn } from "@eumini/ui/lib/utils";
import { Printer, User, Wallet } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Brand } from "./brand";

const LINKS = [
  { href: "/impressoes", label: "Impressões", icon: Printer },
  { href: "/ganhos", label: "Ganhos", icon: Wallet },
  { href: "/conta", label: "Conta", icon: User },
];

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="bg-accent shadow-card">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 sm:px-6">
        <Brand />
        <nav className="flex items-center gap-1 text-sm font-medium text-white">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-1.5 rounded-full px-3 py-2 hover:bg-white/15",
                  active && "bg-white/20",
                )}
              >
                <Icon className="size-4" aria-hidden />
                <span className="hidden sm:inline">{label}</span>
                <span className="sr-only sm:hidden">{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
