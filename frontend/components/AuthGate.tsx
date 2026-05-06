"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { FloatingChatButton } from "@/components/FloatingChatButton";
import { LoginCard } from "@/components/LoginCard";
import { getSession, login, subscribeAuth, type AuthUser } from "@/lib/auth";

type AuthGateProps = {
  children: React.ReactNode;
};

export function AuthGate({ children }: AuthGateProps) {
  const pathname = usePathname();
  const [hydrated, setHydrated] = useState(false);
  const [session, setSession] = useState<AuthUser | null>(null);

  useEffect(() => {
    setSession(getSession());
    setHydrated(true);
    return subscribeAuth(() => setSession(getSession()));
  }, []);

  if (!hydrated) {
    return <p className="px-4 py-6 text-sm text-slate-500">Checking session…</p>;
  }

  if (session) {
    return (
      <>
        {children}
        <FloatingChatButton />
      </>
    );
  }

  // Dedicated login route uses its own layout (see app/login/page.tsx).
  if (pathname === "/login") return <>{children}</>;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <div className="mx-auto max-w-lg px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight text-white">Sign in</h1>
        <p className="mt-1 text-sm text-slate-400">
          Sign in to use StockScope. This is milestone mock auth (localStorage), not a
          production session.
        </p>
        <div className="mt-8">
          <LoginCard
            onLogin={async (email, password) => {
              await login(email, password);
              setSession(getSession());
            }}
          />
        </div>
      </div>
    </div>
  );
}

