"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { login } from "@/lib/auth";

type LoginCardProps = {
  /** Override mock login (e.g. tests or future API-backed login). */
  onLogin?: (email: string, password: string) => void | Promise<void>;
};

export function LoginCard({ onLogin }: LoginCardProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const trimmed = email.trim();
    if (!trimmed) {
      setError("Enter an email.");
      return;
    }
    if (!password) {
      setError("Enter a password.");
      return;
    }

    setLoading(true);
    try {
      if (onLogin) {
        await onLogin(trimmed, password);
      } else {
        await login(trimmed, password);
        router.push("/");
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-gray-200 bg-teal-50/60 p-6 shadow-xl backdrop-blur sm:p-8">
      <h2 className="text-lg font-semibold text-gray-900">Sign in</h2>
      <p className="mt-1 text-sm text-gray-500">
        Signs in through the FastAPI mock auth endpoint; email and token are stored in this
        browser only (localStorage).
      </p>

      <form className="mt-6 space-y-4" onSubmit={(e) => void handleSubmit(e)} noValidate>
        <div>
          <label htmlFor="login-email" className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Email
          </label>
          <input
            id="login-email"
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1.5 w-full rounded-lg border border-teal-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none ring-teal-500/0 transition focus:ring-2 focus:ring-teal-500/40"
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label
            htmlFor="login-password"
            className="text-xs font-medium uppercase tracking-wide text-gray-400"
          >
            Password
          </label>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1.5 w-full rounded-lg border border-teal-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-teal-500/40"
            placeholder="••••••••"
          />
        </div>

        {error && (
          <p className="rounded-lg border border-rose-500/40 bg-rose-950/40 px-3 py-2 text-sm text-rose-200" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-teal-500 py-2.5 text-sm font-semibold text-white shadow-md shadow-teal-500/15 transition hover:bg-teal-400 disabled:opacity-60"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
