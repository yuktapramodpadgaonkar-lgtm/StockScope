import { getApiBase, readErrorMessage } from "@/lib/auth-api";
import type {
  ChatQueryRequest,
  ChatQueryResponse,
  HistoryResponse,
  NewsSentimentResponse,
  ThreadHistoryResponse,
} from "@/lib/revati-types";

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
  };
}

export async function postChatQuery(query: string, threadId?: string | null): Promise<ChatQueryResponse> {
  const body: ChatQueryRequest = { query, thread_id: threadId ?? null };
  const res = await fetch(`${getApiBase()}/api/chat/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
};

export async function postNewsSentiment(body: NewsSentimentRequestBody): Promise<NewsSentimentResponse> {
  const res = await fetch(`${getApiBase()}/api/analysis/news-sentiment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ticker: body.ticker.trim(),
      date_from: body.date_from ?? null,
      date_to: body.date_to ?? null,
      max_articles: body.max_articles ?? 10,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<NewsSentimentResponse>;
}

export async function fetchHistory(): Promise<HistoryResponse> {
  const res = await fetch(`${getApiBase()}/api/history`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<HistoryResponse>;
}

export async function fetchThreadHistory(threadId: string): Promise<ThreadHistoryResponse> {
  const id = threadId.trim();
  const res = await fetch(`${getApiBase()}/api/history/thread/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<ThreadHistoryResponse>;
}
