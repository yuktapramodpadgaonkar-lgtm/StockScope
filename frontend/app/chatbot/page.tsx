"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { ChatWindow } from "@/components/ChatWindow";
import { NewsSentimentReport } from "@/components/NewsSentimentReport";
import { postNewsSentiment } from "@/lib/revati-api";
import type { NewsSentimentResponse } from "@/lib/revati-types";

/** Placeholder threads until persistence exists. TODO: hydrate from GET /api/history or threads API. */
const PLACEHOLDER_THREADS = [
  { id: "thread_001", label: "Why is NVDA up today?" },
  { id: "thread_002", label: "Compare NVDA vs AMD" },
  { id: "thread_003", label: "What’s the sentiment on AAPL?" },
];

export default function ChatbotPage() {
  const [activeThread, setActiveThread] = useState("thread_001");
  const [ticker, setTicker] = useState("NVDA");
  const [dateFrom, setDateFrom] = useState("2026-04-01");
  const [dateTo, setDateTo] = useState("2026-04-11");
  const [sentiment, setSentiment] = useState<NewsSentimentResponse | null>(null);
  const [sentLoading, setSentLoading] = useState(false);
  const [sentError, setSentError] = useState<string | null>(null);

  const loadSentiment = useCallback(async () => {
    const sym = ticker.trim();
    if (!sym) return;
    setSentError(null);
    setSentLoading(true);
    try {
      const data = await postNewsSentiment({
        ticker: sym,
        date_from: dateFrom || null,
        date_to: dateTo || null,
      });
      setSentiment(data);
    } catch (e) {
      setSentError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setSentLoading(false);
    }
  }, [ticker, dateFrom, dateTo]);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-5 sm:px-6 lg:px-8">
          <Link href="/" className="text-sm font-medium text-emerald-400/90 hover:text-emerald-300">
            ← Home
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight text-white">Chatbot</h1>
          <p className="text-sm text-slate-400">
            Week 1 stub: keyword intents, mock citations, and optional mock news sentiment.
          </p>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 lg:flex-row lg:px-8">
        <aside className="w-full shrink-0 space-y-2 lg:w-56">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Threads</p>
          <ul className="space-y-1">
            {PLACEHOLDER_THREADS.map((t) => (
              <li key={t.id}>
                <button
                  type="button"
                  onClick={() => setActiveThread(t.id)}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-xs transition ${
                    activeThread === t.id
                      ? "border-emerald-500/50 bg-emerald-950/40 text-emerald-100"
                      : "border-slate-800 bg-slate-900/50 text-slate-400 hover:border-slate-600"
                  }`}
                >
                  {t.label}
                </button>
              </li>
            ))}
          </ul>
          <p className="text-[10px] text-slate-600">
            TODO: Selecting a thread will load persisted messages once storage ships.
          </p>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col gap-6">
          <ChatWindow initialThreadId={activeThread} key={activeThread} />

          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-200">News sentiment (mock)</h2>
            <div className="flex flex-wrap gap-2">
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="Ticker"
                className="w-28 rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm"
              />
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200"
              />
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200"
              />
              <button
                type="button"
                onClick={() => void loadSentiment()}
                disabled={sentLoading}
                className="rounded-lg bg-slate-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-600 disabled:opacity-40"
              >
                {sentLoading ? "Loading…" : "Run mock analysis"}
              </button>
            </div>
            {sentError ? <p className="text-sm text-rose-400">{sentError}</p> : null}
            {sentiment ? <NewsSentimentReport data={sentiment} /> : null}
          </section>
        </div>
      </div>
    </div>
  );
}
