"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { getSession, logout, subscribeAuth, type AuthUser } from "@/lib/auth";

const NAV_LINKS: { href: string; label: string }[] = [
  { href: "/", label: "Home" },
  { href: "/market-movers", label: "Market movers" },
  { href: "/fundamentals", label: "Fundamentals" },
];

function linkClass(active: boolean): string {
  const base =
    "rounded-lg px-3 py-2 text-sm font-medium transition focus-visible:outline focus-visible:ring-2 focus-visible:ring-emerald-500/50";
  if (active) {
    return `${base} bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30`;
  }
  return `${base} text-slate-300 hover:bg-slate-800/80 hover:text-white`;
}

function shortEmail(email: string): string {
  if (email.length <= 28) return email;
  return `${email.slice(0, 14)}…${email.slice(-10)}`;
}

export function Navbar() {
  const pathname = usePathname();
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    setUser(getSession());
    return subscribeAuth(() => setUser(getSession()));
  }, []);

  function isActive(href: string): boolean {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="text-sm font-semibold tracking-tight text-white hover:text-emerald-200/90"
        >
          StockScope
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-1 sm:gap-2">
          <nav className="flex flex-wrap items-center gap-1 sm:gap-2" aria-label="Main">
            {NAV_LINKS.map(({ href, label }) => (
              <Link key={href} href={href} className={linkClass(isActive(href))}>
                {label}
              </Link>
            ))}
            {!user && (
              <Link href="/login" className={linkClass(isActive("/login"))}>
                Login
              </Link>
            )}
          </nav>
          {user && (
            <div className="flex items-center gap-2 border-l border-slate-800 pl-2 sm:pl-3">
              <span
                className="hidden max-w-[160px] truncate text-xs text-slate-400 sm:inline"
                title={user.email}
              >
                {shortEmail(user.email)}
              </span>
              <button
                type="button"
                onClick={() => logout()}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-300 transition hover:bg-slate-800/80 hover:text-white"
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
