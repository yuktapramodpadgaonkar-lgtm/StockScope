"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { NewsSentimentReport } from "@/components/NewsSentimentReport";
import { fetchHistory, postNewsSentiment } from "@/lib/revati-api";
import type { ChatHistoryItem, HistoryResponse, NewsSentimentResponse } from "@/lib/revati-types";

export default function ChatbotPage() {
  const [activeThread, setActiveThread] = useState("");
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [seedPrompt, setSeedPrompt] = useState<string | null>(null);

  const [ticker, setTicker] = useState("NVDA");
  const [dateFrom, setDateFrom] = useState("2026-04-01");
  const [dateTo, setDateTo] = useState("2026-04-11");
  const [sentiment, setSentiment] = useState<NewsSentimentResponse | null>(null);
  const [sentLoading, setSentLoading] = useState(false);
  const [sentError, setSentError] = useState<string | null>(null);

  const refreshHistory = useCallback(async () => {
    try {
      const h = await fetchHistory();
      setHistory(h);
    } catch {
      /* sidebar shows empty */
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

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

  const threads: ChatHistoryItem[] = history?.chat_history ?? [];

  return (
    <div className="min-h-screen bg-slate-100/90">
      <header className="border-b border-slate-200/90 bg-white shadow-sm">
        <div className="mx-auto max-w-6xl px-4 py-7 sm:px-6 lg:px-8">
          <Link href="/" className="text-sm font-semibold text-teal-700 transition hover:text-teal-800">
            ← Home
          </Link>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            StockScope AI Chatbot
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
            Ask questions about stock movements, sentiment, fundamentals, and portfolio risk
          </p>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 lg:flex-row lg:items-start lg:gap-8 lg:px-8 lg:py-8">
        <ChatSidebar
          threads={threads}
          activeThreadId={activeThread}
          onSelectThread={setActiveThread}
          onNewChat={() => setActiveThread("")}
          onSuggestedPrompt={(text) => setSeedPrompt(text)}
          suggestedDisabled={sentLoading}
          loading={historyLoading}
        />

        <div className="flex min-w-0 flex-1 flex-col gap-6">
          <ChatWindow
            initialThreadId={activeThread}
            onThreadIdChange={(id) => {
              setActiveThread(id);
              void refreshHistory();
            }}
            seedPrompt={seedPrompt}
            onSeedPromptConsumed={() => setSeedPrompt(null)}
          />

          <section className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">News sentiment</h2>
            <p className="mt-1 text-xs text-slate-600">Run a sentiment pass on a ticker (same API as before).</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="Ticker"
                className="w-28 rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2 text-sm shadow-inner focus:border-teal-500/40 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
              />
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2 text-sm text-slate-800 focus:border-teal-500/40 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
              />
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2 text-sm text-slate-800 focus:border-teal-500/40 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
              />
              <button
                type="button"
                onClick={() => void loadSentiment()}
                disabled={sentLoading}
                className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-40"
              >
                {sentLoading ? "Loading…" : "Run analysis"}
              </button>
            </div>
            {sentError ? <p className="mt-3 text-sm text-rose-600">{sentError}</p> : null}
            {sentiment ? (
              <div className="mt-4">
                <NewsSentimentReport data={sentiment} />
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </div>
  );
}
