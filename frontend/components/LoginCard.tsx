"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { login } from "@/lib/auth";

type LoginCardProps = {
  /** Called on successful login to update auth state. */
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

  const inputClassName =
    "mt-2 w-full rounded-xl border border-gray-200 bg-white px-3.5 py-2.5 text-sm text-gray-900 shadow-sm outline-none transition placeholder:text-gray-400 focus:border-teal-600 focus:ring-2 focus:ring-teal-600/20 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100 dark:placeholder:text-gray-500 dark:focus:border-teal-500 dark:focus:ring-teal-500/25";

  const labelClassName =
    "text-sm font-medium text-gray-700 dark:text-gray-300";

  return (
    <div className="w-full rounded-2xl border border-gray-200/90 bg-white p-8 shadow-lg shadow-gray-200/40 dark:border-gray-800 dark:bg-gray-900 dark:shadow-black/30 sm:p-10">
      <div className="mb-8 flex flex-col items-center text-center">
        <div
          className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-700 text-lg font-bold text-white shadow-md shadow-teal-900/20 dark:bg-teal-600 dark:shadow-teal-950/40"
          aria-hidden
        >
          S
        </div>
        <p className="text-sm font-semibold tracking-wide text-teal-700 dark:text-teal-400">
          StockScope
        </p>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
          Welcome back
        </h1>
        <p className="mt-2 max-w-sm text-sm leading-relaxed text-gray-600 dark:text-gray-400">
          Log in to continue your financial research
        </p>
      </div>

      <form className="space-y-5" onSubmit={(e) => void handleSubmit(e)} noValidate>
        <div>
          <label htmlFor="login-email" className={labelClassName}>
            Email
          </label>
          <input
            id="login-email"
            name="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClassName}
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label htmlFor="login-password" className={labelClassName}>
            Password
          </label>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClassName}
            placeholder="••••••••"
          />
        </div>

        {error ? (
          <p
            className="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-800 dark:border-rose-500/35 dark:bg-rose-950/50 dark:text-rose-200"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-teal-700 py-3 text-sm font-semibold text-white shadow-md shadow-teal-900/15 transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-teal-600 dark:shadow-teal-950/30 dark:hover:bg-teal-500"
        >
          {loading ? "Signing in…" : "Log in"}
        </button>
      </form>

      <p className="mt-8 text-center text-sm text-gray-600 dark:text-gray-400">
        Don&apos;t have an account?{" "}
        <Link
          href="/signup"
          className="font-semibold text-teal-700 underline-offset-4 hover:text-teal-800 hover:underline dark:text-teal-400 dark:hover:text-teal-300"
        >
          Sign up
        </Link>
      </p>
    </div>
  );
}
