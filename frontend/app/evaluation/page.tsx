"use client";

import Link from "next/link";
import { useState } from "react";

import { postCompareModels, type CompareResponse, type EvalTask, type ModelResult } from "@/lib/evaluation-api";

const TASK_OPTIONS: { value: EvalTask; label: string }[] = [
  { value: "chat", label: "Chat" },
  { value: "sentiment", label: "News Sentiment" },
  { value: "buy_sell", label: "Buy / Sell" },
  { value: "fundamental", label: "Fundamental" },
];

const MODEL_LABELS: Record<string, string> = {
  gemini: "Gemini 1.5 Flash",
  llama: "LLaMA 3.1 8B",
  mistral: "Mistral 7B",
};

function SafetyBadge({ passed }: { passed: boolean }) {
  return passed ? (
    <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
      Passed
    </span>
  ) : (
    <span className="inline-flex items-center rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">
      Failed
    </span>
  );
}

function ModelCard({ result }: { result: ModelResult }) {
  const [expanded, setExpanded] = useState(false);
  const displayName = MODEL_LABELS[result.model] ?? result.model;

  return (
    <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-base font-semibold text-slate-900">{displayName}</p>
          <p className="mt-0.5 font-mono text-xs text-slate-500">{result.model}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="text-center">
            <p className="text-lg font-bold text-teal-700">{result.latency_ms.toLocaleString()}</p>
            <p className="text-[10px] uppercase tracking-wide text-slate-500">ms</p>
          </div>
          <div className="text-center">
            <p className="text-lg font-bold text-slate-800">{result.citation_count}</p>
            <p className="text-[10px] uppercase tracking-wide text-slate-500">citations</p>
          </div>
          <SafetyBadge passed={result.safety_passed} />
        </div>
      </div>

      {result.error ? (
        <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
          {result.error}
        </p>
      ) : (
        <>
          <p
            className={`mt-3 text-sm leading-relaxed text-slate-700 ${!expanded ? "line-clamp-4" : ""}`}
          >
            {result.response}
          </p>
          {result.response.length > 280 ? (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="mt-2 text-xs font-semibold text-teal-700 hover:text-teal-800"
            >
              {expanded ? "Show less" : "Show full response"}
            </button>
          ) : null}
        </>
      )}
    </div>
  );
}

function ComparisonTable({ results }: { results: ModelResult[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200/90 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 bg-slate-50">
            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              Model
            </th>
            <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
              Latency (ms)
            </th>
            <th className="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
              Citations
            </th>
            <th className="px-5 py-3 text-center text-xs font-semibold uppercase tracking-wide text-slate-500">
              Safety
            </th>
            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {results.map((r) => (
            <tr key={r.model} className="hover:bg-slate-50/60">
              <td className="px-5 py-3 font-medium text-slate-900">
                {MODEL_LABELS[r.model] ?? r.model}
              </td>
              <td className="px-5 py-3 text-right font-mono text-slate-700">
                {r.latency_ms.toLocaleString()}
              </td>
              <td className="px-5 py-3 text-right text-slate-700">{r.citation_count}</td>
              <td className="px-5 py-3 text-center">
                <SafetyBadge passed={r.safety_passed} />
              </td>
              <td className="px-5 py-3">
                {r.error ? (
                  <span className="text-xs text-rose-600">Error</span>
                ) : (
                  <span className="text-xs text-emerald-600">OK</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function EvaluationPage() {
  const [task, setTask] = useState<EvalTask>("sentiment");
  const [ticker, setTicker] = useState("NVDA");
  const [query, setQuery] = useState("What is the market sentiment for this stock?");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CompareResponse | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const sym = ticker.trim().toUpperCase();
    const q = query.trim();
    if (!sym || !q) return;
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const data = await postCompareModels({ task, ticker: sym, query: q });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100/90">
      <header className="border-b border-slate-200/90 bg-white shadow-sm">
        <div className="mx-auto max-w-5xl px-4 py-7 sm:px-6 lg:px-8">
          <Link
            href="/"
            className="text-sm font-semibold text-teal-700 transition hover:text-teal-800"
          >
            ← Home
          </Link>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Model Evaluation
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
            Run the same prompt through Gemini, LLaMA, and Mistral and compare latency, citations,
            and safety side-by-side.
          </p>
        </div>
      </header>

      <div className="mx-auto max-w-5xl space-y-8 px-4 py-8 sm:px-6 lg:px-8">
        {/* Input form */}
        <section className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Configure comparison</h2>
          <form onSubmit={onSubmit} className="mt-5 space-y-5">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Task type
                </label>
                <select
                  value={task}
                  onChange={(e) => setTask(e.target.value as EvalTask)}
                  className="rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-sm text-slate-800 shadow-inner focus:border-teal-500/40 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                >
                  {TASK_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Ticker
                </label>
                <input
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  placeholder="e.g. AAPL"
                  maxLength={16}
                  className="rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-sm text-slate-800 shadow-inner focus:border-teal-500/40 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
                />
              </div>

              <div className="flex flex-col gap-1.5 sm:col-span-1">
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  &nbsp;
                </label>
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:opacity-40"
                >
                  {loading ? "Running…" : "Run comparison"}
                </button>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Query
              </label>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={3}
                maxLength={1000}
                className="rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-sm text-slate-800 shadow-inner focus:border-teal-500/40 focus:outline-none focus:ring-2 focus:ring-teal-500/20"
              />
            </div>
          </form>
        </section>

        {error ? (
          <div
            className="rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-900 shadow-sm"
            role="alert"
          >
            <p className="font-semibold">Request failed</p>
            <p className="mt-1 text-rose-800/90">{error}</p>
          </div>
        ) : null}

        {loading ? (
          <div className="space-y-4">
            {["gemini", "llama", "mistral"].map((m) => (
              <div
                key={m}
                className="h-36 animate-pulse rounded-2xl border border-slate-200/90 bg-white shadow-sm"
              />
            ))}
          </div>
        ) : null}

        {result && !loading ? (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-lg bg-slate-100 px-2.5 py-1 font-mono text-xs font-semibold text-slate-700">
                {result.ticker}
              </span>
              <span className="rounded-lg bg-teal-50 px-2.5 py-1 text-xs font-semibold text-teal-700 ring-1 ring-teal-200">
                {result.task}
              </span>
            </div>

            {/* Summary table */}
            <ComparisonTable results={result.results} />

            {/* Per-model response cards */}
            <div className="space-y-4">
              {result.results.map((r) => (
                <ModelCard key={r.model} result={r} />
              ))}
            </div>

            <p className="text-xs text-slate-400">{result.disclaimer}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
