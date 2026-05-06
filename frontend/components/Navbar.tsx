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
    "rounded-lg px-3 py-2 text-sm font-medium transition focus-visible:outline focus-visible:ring-2 focus-visible:ring-teal-500/50";
  if (active) {
    return `${base} bg-teal-100 text-teal-700 ring-1 ring-teal-400/50`;
  }
  return `${base} text-gray-700 hover:bg-teal-100/80 hover:text-teal-800`;
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
    <header className="sticky top-0 z-40 border-b border-gray-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="text-sm font-semibold tracking-tight text-gray-900 hover:text-teal-700"
        >
          StockScope AI
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
            <div className="flex items-center gap-2 border-l border-gray-200 pl-2 sm:pl-3">
              <span
                className="hidden max-w-[160px] truncate text-xs text-gray-500 sm:inline"
                title={user.email}
              >
                {shortEmail(user.email)}
              </span>
              <button
                type="button"
                onClick={() => logout()}
                className="rounded-lg px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-teal-100/80 hover:text-teal-800"
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
