"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { HistoryFilterTabs } from "@/components/history/HistoryFilterTabs";
import { HistoryList } from "@/components/history/HistoryList";
import { HistorySearchBar } from "@/components/history/HistorySearchBar";
import type { HistoryFilterTab } from "@/components/history/historyUtils";
import { matchesFilter, matchesSearch, mergeHistoryItems } from "@/components/history/historyUtils";
import { fetchHistory, fetchMemorySummary } from "@/lib/revati-api";
import type { HistoryResponse, MemorySummaryResponse } from "@/lib/revati-types";

export default function HistoryPage() {
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [memory, setMemory] = useState<MemorySummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterTab, setFilterTab] = useState<HistoryFilterTab>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const h = await fetchHistory();
        let mem: MemorySummaryResponse | null = null;
        try {
          mem = await fetchMemorySummary("default");
        } catch {
          mem = null;
        }
        if (!cancelled) {
          setData(h);
          setMemory(mem);
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

  const merged = useMemo(() => mergeHistoryItems(data), [data]);

  const filtered = useMemo(() => {
    return merged.filter((item) => matchesFilter(item, filterTab) && matchesSearch(item, search));
  }, [merged, filterTab, search]);

  const hasActiveFilters = filterTab !== "all" || search.trim().length > 0;

  return (
    <div className="min-h-screen bg-slate-100/80">
      <div className="border-b border-slate-200/90 bg-white/95 shadow-sm">
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
          <Link
            href="/"
            className="text-sm font-semibold text-teal-700 transition hover:text-teal-800"
          >
            ← Home
          </Link>
          <h1 className="mt-4 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Research History
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
            View previous chatbot queries, stock analyses, and saved research activity.
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-4xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {error ? (
          <div
            className="rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-900 shadow-sm"
            role="alert"
          >
            <p className="font-semibold">Could not load history</p>
            <p className="mt-1 text-rose-800/90">{error}</p>
            <p className="mt-3 text-xs text-rose-700/80">
              Check that the API is running and <code className="rounded bg-rose-100 px-1">NEXT_PUBLIC_API_BASE_URL</code>{" "}
              is correct.
            </p>
          </div>
        ) : null}

        {!error ? (
          <>
            {memory ? (
              <section
                className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm"
                aria-label="Session memory summary"
              >
                <h2 className="text-sm font-semibold text-slate-900">Session memory (default)</h2>
                <p className="mt-1 text-xs text-slate-500">
                  Used to tailor explanations only — not for recommendations. Resets when session storage is cleared on the
                  server.
                </p>
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Frequent tickers</dt>
                    <dd className="mt-1 font-mono text-slate-800">
                      {memory.frequent_tickers.length ? memory.frequent_tickers.join(", ") : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Preferred topics</dt>
                    <dd className="mt-1 font-mono text-slate-800">
                      {memory.preferred_topics.length ? memory.preferred_topics.join(", ") : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Risk tone</dt>
                    <dd className="mt-1 text-slate-800">{memory.risk_style ?? "—"}</dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">Updated</dt>
                    <dd className="mt-1 text-slate-600">{memory.last_updated || "—"}</dd>
                  </div>
                </dl>
              </section>
            ) : null}

            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <HistoryFilterTabs value={filterTab} onChange={setFilterTab} />
              <div className="w-full lg:max-w-sm">
                <HistorySearchBar value={search} onChange={setSearch} />
              </div>
            </div>

            <HistoryList
              items={filtered}
              loading={loading}
              emptyState={{
                title: "No activity yet",
                description:
                  "Run a chat query, sentiment check, or analysis from the app—your research trail will show up here.",
              }}
              filteredEmptyMessage={{
                title: "No history found",
                description: "Nothing matches your filters or search. Try another tab or clear the search box.",
              }}
              hasActiveFilters={hasActiveFilters}
            />
          </>
        ) : null}
      </div>
    </div>
  );
}
