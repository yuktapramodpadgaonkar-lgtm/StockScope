export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: { email: string };
};

export function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  return base.replace(/\/$/, "");
}

async function readErrorMessage(res: Response): Promise<string> {
  const text = await res.text();
  try {
    const j = JSON.parse(text) as { detail?: unknown };
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((x: { msg?: string }) => (typeof x?.msg === "string" ? x.msg : ""))
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    /* use raw text */
  }
  return text || `Request failed (${res.status})`;
}

/** POST /api/auth/login — same contract as FastAPI mock auth. */
export async function apiLogin(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${getApiBase()}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim(), password }),
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<LoginResponse>;
}

/** Optional: notify backend (stateless mock — safe to skip if offline). */
export function apiLogoutFireAndForget(): void {
  void fetch(`${getApiBase()}/api/auth/logout`, { method: "POST" }).catch(() => {});
}
