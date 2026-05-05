import type { ChatQueryResponse } from "@/lib/revati-types";

export function buildAssistantPayloadFromHistoryText(
  text: string,
  threadId: string,
  timestamp: string,
): ChatQueryResponse {
  return {
    thread_id: threadId,
    detected_intent: "unknown",
    tickers: [],
    answer: text,
    summary_bullets: [],
    citations: [],
    disclaimer: "",
    timestamp,
  };
}

export function isRichAssistantPayload(payload: ChatQueryResponse): boolean {
  const bullets = payload.summary_bullets ?? [];
  const cites = payload.citations ?? [];
  const tickers = payload.tickers ?? [];
  return (
    payload.detected_intent !== "unknown" ||
    bullets.length > 0 ||
    cites.length > 0 ||
    tickers.length > 0
  );
}

export function formatMessageTime(iso: string): string {
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return iso;
  return new Date(d).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
