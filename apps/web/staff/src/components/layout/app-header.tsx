"use client";

import { cn } from "@eumini/ui/lib/utils";
import { useLogout } from "@eumini/web-core/auth-client";
import { CalendarCheck, LogOut, Package, Tags, Users } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Brand } from "./brand";

const LINKS = [
  { href: "/hoje", label: "Hoje", icon: CalendarCheck },
  { href: "/pedidos", label: "Pedidos", icon: Package },
  { href: "/parceiros", label: "Parceiros", icon: Users },
  { href: "/tarifas", label: "Tarifas", icon: Tags },
];

export function AppHeader() {
  const pathname = usePathname();
  const logout = useLogout();

  return (
    <header className="bg-accent shadow-card">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-2 px-4 sm:px-6">
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
                <span className="hidden md:inline">{label}</span>
                <span className="sr-only md:hidden">{label}</span>
              </Link>
            );
          })}
          <button
            type="button"
            onClick={() => logout.mutate("/entrar")}
            className="flex items-center gap-1.5 rounded-full px-3 py-2 hover:bg-white/15"
          >
            <LogOut className="size-4" aria-hidden />
            <span className="sr-only">Sair</span>
          </button>
        </nav>
      </div>
    </header>
  );
}
