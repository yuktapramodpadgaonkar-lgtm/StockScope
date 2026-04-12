"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { HistoryList } from "@/components/HistoryList";
import { fetchHistory } from "@/lib/revati-api";
import type {
  ChatHistoryItem,
  HistoryResponse,
  ResearchHistoryItem,
  SavedPromptItem,
} from "@/lib/revati-types";

export default function HistoryPage() {
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const h = await fetchHistory();
        if (!cancelled) {
          setData(h);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load history");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const chatRows = useMemo(
    () =>
      (data?.chat_history ?? []).map((c: ChatHistoryItem) => ({
        id: c.thread_id,
        title: c.title,
        subtitle: `Updated ${c.last_updated} · ${c.thread_id}`,
      })),
    [data],
  );

  const researchRows = useMemo(
    () =>
      (data?.research_history ?? []).map((r: ResearchHistoryItem) => ({
        id: r.id,
        title: `${r.type} · ${r.ticker}`,
        subtitle: r.created_at,
      })),
    [data],
  );

  const promptRows = useMemo(
    () =>
      (data?.saved_prompts ?? []).map((p: SavedPromptItem) => ({
        id: p.id,
        title: p.title,
        subtitle: p.prompt_text,
      })),
    [data],
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
          <Link href="/" className="text-sm font-medium text-emerald-400/90 hover:text-emerald-300">
            ← Home
          </Link>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white">History</h1>
          <p className="mt-1 text-sm text-slate-400">
            Mock records from <code className="text-emerald-400/80">GET /api/history</code> for UI wiring.
          </p>
        </div>
      </header>

      <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {error ? <p className="text-sm text-rose-400">{error}</p> : null}

        <HistoryList title="Chat history" loading={loading} rows={chatRows} emptyMessage="No chat threads yet." />

        <HistoryList
          title="Research history"
          loading={loading}
          rows={researchRows}
          emptyMessage="No research runs yet."
        />

        <HistoryList title="Saved prompts" loading={loading} rows={promptRows} emptyMessage="No saved prompts yet." />
      </div>
    </div>
  );
}
