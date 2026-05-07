import { getApiBase, readErrorMessage } from "@/lib/auth-api";
import { getAccessToken } from "@/lib/auth";
import type {
  ChatQueryRequest,
  ChatQueryResponse,
  HistoryResponse,
  MemorySummaryResponse,
  NewsSentimentResponse,
  ThreadHistoryResponse,
} from "@/lib/revati-types";

function authHeaders(): HeadersInit {
  const token = getAccessToken();
  return token
    ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` }
    : { "Content-Type": "application/json" };
}

function normalizeChatQueryResponse(raw: unknown): ChatQueryResponse {
  const r = raw as Record<string, unknown>;
  const citations = Array.isArray(r.citations) ? r.citations : [];
  const bullets = Array.isArray(r.summary_bullets) ? r.summary_bullets : [];
  const tickers = Array.isArray(r.tickers) ? r.tickers : [];
  const intent = (r.detected_intent as ChatQueryResponse["detected_intent"]) ?? "unknown";
  return {
    thread_id: String(r.thread_id ?? ""),
    detected_intent: intent,
    tickers: tickers.map(String),
    answer: String(r.answer ?? ""),
    summary_bullets: bullets.map(String),
    citations: citations.map((c) => {
      const x = c as Record<string, unknown>;
      return {
        title: String(x.title ?? ""),
        url: String(x.url ?? "#"),
        source: String(x.source ?? ""),
        published_at: String(x.published_at ?? ""),
      };
    }),
    disclaimer: String(r.disclaimer ?? ""),
    timestamp: String(r.timestamp ?? new Date().toISOString()),
    llm_model_used: r.llm_model_used != null ? String(r.llm_model_used) : null,
    llm_provider: r.llm_provider != null ? String(r.llm_provider) : null,
    llm_fallback_used: Boolean(r.llm_fallback_used),
  };
}

export async function postChatQuery(query: string, threadId?: string | null): Promise<ChatQueryResponse> {
  const body: ChatQueryRequest = { query, thread_id: threadId ?? null };
  const res = await fetch(`${getApiBase()}/api/chat/query`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  let data: unknown;
  try {
    data = await res.json();
  } catch {
    throw new Error("Invalid response from chat API. Is the backend running?");
  }
  return normalizeChatQueryResponse(data);
}

export type NewsSentimentRequestBody = {
  ticker: string;
  date_from?: string | null;
  date_to?: string | null;
  max_articles?: number;
  /** Hybrid ingest + retrieve to ground theme LLM on chunk text + URLs. */
  use_rag?: boolean;
  /** LLM for theme generation: gemini | llama | mistral */
  model_name?: string | null;
};

export async function postNewsSentiment(body: NewsSentimentRequestBody): Promise<NewsSentimentResponse> {
  const res = await fetch(`${getApiBase()}/api/analysis/news-sentiment`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      ticker: body.ticker.trim(),
      date_from: body.date_from ?? null,
      date_to: body.date_to ?? null,
      max_articles: body.max_articles ?? 10,
      use_rag: body.use_rag ?? true,
      model_name: body.model_name ?? null,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<NewsSentimentResponse>;
}

export async function fetchHistory(): Promise<HistoryResponse> {
  const res = await fetch(`${getApiBase()}/api/history`, { headers: authHeaders(), cache: "no-store" });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<HistoryResponse>;
}

export async function fetchThreadHistory(threadId: string): Promise<ThreadHistoryResponse> {
  const id = threadId.trim();
  const res = await fetch(`${getApiBase()}/api/history/thread/${encodeURIComponent(id)}`, { headers: authHeaders(), cache: "no-store" });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<ThreadHistoryResponse>;
}

export async function fetchMemorySummary(sessionId: string = "default"): Promise<MemorySummaryResponse> {
  const sid = sessionId.trim() || "default";
  const res = await fetch(
    `${getApiBase()}/api/history/memory-summary?session_id=${encodeURIComponent(sid)}`,
    { headers: authHeaders(), cache: "no-store" },
  );
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<MemorySummaryResponse>;
}
