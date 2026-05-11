import { getApiBase, readErrorMessage } from "@/lib/auth-api";
import { getAccessToken } from "@/lib/auth";

function authHeaders(): HeadersInit {
  const token = getAccessToken();
  return token
    ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` }
    : { "Content-Type": "application/json" };
}

export type AgenticResearchRequest = {
  ticker: string;
  question: string;
  session_id?: string;
  preferred_model?: string;
  max_steps?: number;
  require_two_tools?: boolean;
  include_buy_sell?: boolean;
  include_news?: boolean;
  include_fundamental?: boolean;
  secondary_ticker?: string | null;
};

export type AgenticResearchResponse = {
  ticker: string;
  question: string;
  plan: { steps: { tool: string; args: Record<string, unknown> }[] };
  answer: string;
  citations: { title: string; url: string; source?: string | null; published_at?: string | null }[];
  citations_used: number[];
  critic_passed: boolean;
  first_critic_passed: boolean;
  final_critic_passed: boolean;
  repair_attempted: boolean;
  plan_retry_attempted: boolean;
  critic_notes: string[];
  failed_checks: string[];
  memory_profile: Record<string, unknown>;
  model_used: string | null;
  provider: string | null;
  latency_ms: number;
};

export async function postAgenticResearch(body: AgenticResearchRequest): Promise<AgenticResearchResponse> {
  const res = await fetch(`${getApiBase()}/api/agentic-research/run`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      ticker: body.ticker.trim().toUpperCase(),
      question: body.question.trim(),
      session_id: body.session_id ?? "default",
      preferred_model: body.preferred_model ?? "llama",
      max_steps: body.max_steps ?? 3,
      require_two_tools: body.require_two_tools ?? true,
      include_buy_sell: body.include_buy_sell ?? true,
      include_news: body.include_news ?? true,
      include_fundamental: body.include_fundamental ?? true,
      secondary_ticker: body.secondary_ticker?.trim().toUpperCase() || undefined,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<AgenticResearchResponse>;
}
