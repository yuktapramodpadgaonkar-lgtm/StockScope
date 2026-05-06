import type {
  ChatHistoryItem,
  HistoryResponse,
  ResearchHistoryItem,
  SavedPromptItem,
} from "@/lib/revati-types";

export type HistoryFilterTab = "all" | "chat" | "sentiment" | "fundamental" | "buy_sell";

export type UnifiedHistoryItem =
  | { kind: "chat"; data: ChatHistoryItem }
  | { kind: "research"; data: ResearchHistoryItem }
  | { kind: "prompt"; data: SavedPromptItem };

export function researchTabCategory(type: string): "sentiment" | "fundamental" | "buy_sell" | "other" {
  const t = type.toLowerCase();
  if (t.includes("sentiment") || t === "news" || t.includes("news_sentiment")) return "sentiment";
  if (t.includes("fundamental")) return "fundamental";
  if (t.includes("buy") || t.includes("sell")) return "buy_sell";
  return "other";
}

export function analysisTypeLabel(kind: UnifiedHistoryItem["kind"], researchType?: string): string {
  if (kind === "chat") return "Chat";
  if (kind === "prompt") return "Saved";
  const cat = researchTabCategory(researchType ?? "");
  if (cat === "sentiment") return "Sentiment";
  if (cat === "fundamental") return "Fundamental";
  if (cat === "buy_sell") return "Buy/Sell";
  return "Research";
}

export function mergeHistoryItems(data: HistoryResponse | null): UnifiedHistoryItem[] {
  if (!data) return [];
  const chat: UnifiedHistoryItem[] = data.chat_history.map((c) => ({ kind: "chat", data: c }));
  const research: UnifiedHistoryItem[] = data.research_history.map((r) => ({ kind: "research", data: r }));
  const prompts: UnifiedHistoryItem[] = data.saved_prompts.map((p) => ({ kind: "prompt", data: p }));

  const ts = (item: UnifiedHistoryItem): number => {
    if (item.kind === "chat") return Date.parse(item.data.last_updated) || 0;
    if (item.kind === "research") return Date.parse(item.data.created_at) || 0;
    return 0;
  };

  const dated = [...chat, ...research].sort((a, b) => ts(b) - ts(a));
  return [...dated, ...prompts];
}

export function matchesFilter(item: UnifiedHistoryItem, tab: HistoryFilterTab): boolean {
  if (tab === "all") return true;
  if (tab === "chat") return item.kind === "chat";
  if (item.kind !== "research") return false;
  return researchTabCategory(item.data.type) === tab;
}

export function matchesSearch(item: UnifiedHistoryItem, q: string): boolean {
  if (!q.trim()) return true;
  const needle = q.trim().toLowerCase();
  if (item.kind === "chat") {
    const t = item.data.title.toLowerCase();
    const id = item.data.thread_id.toLowerCase();
    return t.includes(needle) || id.includes(needle);
  }
  if (item.kind === "research") {
    const ticker = item.data.ticker.toLowerCase();
    const typ = item.data.type.toLowerCase();
    return ticker.includes(needle) || typ.includes(needle);
  }
  return (
    item.data.title.toLowerCase().includes(needle) || item.data.prompt_text.toLowerCase().includes(needle)
  );
}

const URL_RE = /https?:\/\/[^\s\])"'<>]+/gi;

export function extractUrls(...texts: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const text of texts) {
    if (!text) continue;
    const matches = text.match(URL_RE);
    if (!matches) continue;
    for (const u of matches) {
      const clean = u.replace(/[.,;:!?)]+$/, "");
      if (!seen.has(clean)) {
        seen.add(clean);
        out.push(clean);
      }
    }
  }
  return out;
}

export function previewText(text: string, max = 140): string {
  const t = text.replace(/\s+/g, " ").trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

export function formatHistoryTimestamp(iso: string): string {
  const d = Date.parse(iso);
  if (Number.isNaN(d)) return iso;
  return new Date(d).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
