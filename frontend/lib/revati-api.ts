import type {
  ChatQueryRequest,
  ChatQueryResponse,
  HistoryResponse,
  NewsSentimentResponse,
} from "@/lib/revati-types";

function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  return base.replace(/\/$/, "");
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
    const text = await res.text();
    throw new Error(text || `Chat request failed (${res.status})`);
  }
  return res.json() as Promise<ChatQueryResponse>;
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
    const text = await res.text();
    throw new Error(text || `News sentiment request failed (${res.status})`);
  }
  return res.json() as Promise<NewsSentimentResponse>;
}

export async function fetchHistory(): Promise<HistoryResponse> {
  const res = await fetch(`${getApiBase()}/api/history`, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `History request failed (${res.status})`);
  }
  return res.json() as Promise<HistoryResponse>;
}
