/**
 * Client session: localStorage + FastAPI mock auth (`POST /api/auth/login`).
 * Replace with secure httpOnly cookies when you move beyond the milestone.
 */

import { apiLogin, apiLogoutFireAndForget } from "@/lib/auth-api";

export type AuthUser = {
  email: string;
  /** Present after API login; used for `Authorization: Bearer` on protected calls later. */
  access_token?: string;
};

const STORAGE_KEY = "stockscope_mock_session";
const AUTH_EVENT = "stockscope-auth-change";

function emitAuthChange(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_EVENT));
}

/** Subscribe to login/logout from any tab in this window. */
export function subscribeAuth(listener: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(AUTH_EVENT, listener);
  return () => window.removeEventListener(AUTH_EVENT, listener);
}

function parseStored(raw: string): AuthUser | null {
  try {
    const parsed = JSON.parse(raw) as AuthUser & { access_token?: string };
    if (!parsed?.email || typeof parsed.email !== "string") return null;
    const u: AuthUser = { email: parsed.email };
    if (typeof parsed.access_token === "string") u.access_token = parsed.access_token;
    return u;
  } catch {
    return null;
  }
}

export function getSession(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  return parseStored(raw);
}

/** Bearer token for API calls (if logged in via backend). */
export function getAccessToken(): string | null {
  return getSession()?.access_token ?? null;
}

/**
 * Sign in via `POST /api/auth/login`, then persist email + access_token locally.
 */
export async function login(email: string, password: string): Promise<AuthUser> {
  if (typeof window === "undefined") {
    throw new Error("login() must run in the browser");
  }
  const trimmed = email.trim();
  if (!trimmed || !password) {
    throw new Error("Email and password are required.");
  }

  const data = await apiLogin(trimmed, password);
  const user: AuthUser = {
    email: data.user.email,
    access_token: data.access_token,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  emitAuthChange();
  return user;
}

export function logout(): void {
  if (typeof window === "undefined") return;
  const hadToken = Boolean(getAccessToken());
  localStorage.removeItem(STORAGE_KEY);
  emitAuthChange();
  if (hadToken) {
    apiLogoutFireAndForget();
  }
}
