"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  fetchMockBuySellReport,
  type BuySellReport,
  type Recommendation,
} from "@/lib/buy-sell-api";

function scoreBar(label: string, value: number, weight?: number) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-slate-400">
        <span>{label}</span>
        <span>
          {value}
          {weight != null ? ` / weight ${weight}%` : ""}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-emerald-500/90 transition-all"
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  );
}

function recBadge(rec: Recommendation) {
  const map: Record<Recommendation, string> = {
    BUY: "bg-emerald-500/20 text-emerald-300 ring-emerald-500/40",
    HOLD: "bg-amber-500/20 text-amber-200 ring-amber-500/40",
    SELL: "bg-rose-500/20 text-rose-200 ring-rose-500/40",
  };
  return (
    <span
      className={`inline-flex rounded-lg px-3 py-1 text-sm font-bold ring-1 ${map[rec]}`}
    >
      {rec}
    </span>
  );
}

export function BuySellReportView() {
  const [report, setReport] = useState<BuySellReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMockBuySellReport();
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="mx-auto min-h-screen max-w-4xl px-4 py-10 text-slate-100">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-widest text-emerald-400/90">
            Buy / Sell analysis
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Kavout-style report (Phase 1 mock)
          </h1>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:border-slate-500"
          >
            Reload mock
          </button>
          <Link
            href="/"
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:border-slate-500"
          >
            Home
          </Link>
        </div>
      </div>

      {loading && (
        <p className="text-slate-400" aria-live="polite">
          Loading report…
        </p>
      )}
      {error && (
        <div className="rounded-lg border border-rose-500/40 bg-rose-950/40 px-4 py-3 text-rose-200">
          {error}
        </div>
      )}

      {report && !loading && (
        <div className="space-y-8">
          {/* Disclaimer */}
          <aside className="rounded-xl border border-amber-500/30 bg-amber-950/30 px-4 py-3 text-sm text-amber-100/95">
            <p className="font-medium text-amber-200">Disclaimer</p>
            <p className="mt-1 text-amber-100/90">{report.disclaimer}</p>
          </aside>

          {/* Headline */}
          <header className="rounded-2xl border border-slate-700/80 bg-slate-900/60 p-6 shadow-xl">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm text-slate-400">
                  Ticker · schema {report.schema_version}
                </p>
                <p className="mt-1 text-3xl font-bold tracking-tight text-white">
                  {report.ticker}
                </p>
              </div>
              {recBadge(report.recommendation)}
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              {scoreBar("Confidence", report.confidence)}
              {scoreBar("Setup quality", report.setup_quality)}
              <div className="space-y-1">
                <p className="text-xs text-slate-400">Optimal timeframe</p>
                <p className="text-lg font-medium text-white">
                  {report.optimal_timeframe}
                </p>
              </div>
            </div>
          </header>

          {/* Thesis */}
          <section className="rounded-2xl border border-slate-700/80 bg-slate-900/40 p-6">
            <h2 className="text-lg font-semibold text-white">Investment thesis</h2>
            <p className="mt-3 text-slate-300">{report.investment_thesis.summary}</p>
            <ul className="mt-4 list-inside list-disc space-y-2 text-slate-400">
              {report.investment_thesis.key_drivers.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </section>

          {/* Three pillars */}
          <div className="grid gap-6 lg:grid-cols-3">
            <section className="rounded-2xl border border-slate-700/80 bg-slate-900/40 p-5">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                Fundamentals ({report.fundamental_analysis.weight}%)
              </h3>
              {scoreBar("Score", report.fundamental_analysis.score)}
              <p className="mt-4 text-sm text-slate-300">
                {report.fundamental_analysis.business_performance}
              </p>
              <dl className="mt-4 space-y-2 text-xs text-slate-400">
                <div className="flex justify-between gap-2">
                  <dt>P/E</dt>
                  <dd className="text-slate-200">
                    {report.fundamental_analysis.valuation_analysis.pe ?? "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>DCF value</dt>
                  <dd className="text-slate-200">
                    {report.fundamental_analysis.valuation_analysis.dcf_value ?? "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>Price</dt>
                  <dd className="text-slate-200">
                    {report.fundamental_analysis.valuation_analysis.current_price ?? "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-2">
                  <dt>Implied upside %</dt>
                  <dd className="text-slate-200">
                    {report.fundamental_analysis.valuation_analysis.implied_upside ?? "—"}
                  </dd>
                </div>
              </dl>
              <p className="mt-3 text-xs text-slate-500">
                {report.fundamental_analysis.bull_bear_integration}
              </p>
              <p className="mt-4 text-sm font-medium text-emerald-200/90">
                {report.fundamental_analysis.verdict}
              </p>
            </section>

            <section className="rounded-2xl border border-slate-700/80 bg-slate-900/40 p-5">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                Technicals ({report.technical_analysis.weight}%)
              </h3>
              {scoreBar("Score", report.technical_analysis.score)}
              <p className="mt-4 text-sm text-slate-300">
                {report.technical_analysis.trend_analysis}
              </p>
              <dl className="mt-4 space-y-1 text-xs text-slate-400">
                <div>RSI: {report.technical_analysis.indicators.rsi ?? "—"}</div>
                <div>MACD: {report.technical_analysis.indicators.macd_signal || "—"}</div>
                <div>MA 50: {report.technical_analysis.indicators.ma_50 ?? "—"}</div>
                <div>MA 200: {report.technical_analysis.indicators.ma_200 ?? "—"}</div>
                <div>Price vs MA: {report.technical_analysis.indicators.price_vs_ma || "—"}</div>
              </dl>
              <p className="mt-4 text-sm font-medium text-emerald-200/90">
                {report.technical_analysis.verdict}
              </p>
            </section>

            <section className="rounded-2xl border border-slate-700/80 bg-slate-900/40 p-5">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
                Sentiment ({report.sentiment_analysis.weight}%)
              </h3>
              {scoreBar("Score", report.sentiment_analysis.score)}
              <ul className="mt-4 space-y-2 text-sm text-slate-300">
                {report.sentiment_analysis.recent_developments.map((line) => (
                  <li key={line} className="border-l-2 border-slate-600 pl-3">
                    {line}
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-sm font-medium text-emerald-200/90">
                {report.sentiment_analysis.verdict}
              </p>
            </section>
          </div>

          {/* Final verdict */}
          <section className="rounded-2xl border border-emerald-500/25 bg-emerald-950/20 p-6">
            <h2 className="text-lg font-semibold text-emerald-200">Final verdict</h2>
            <div className="mt-4 flex flex-wrap items-center gap-4">
              {scoreBar("Overall score", report.final_verdict.overall_score)}
              <span className="text-sm text-slate-400">
                Rating: <strong className="text-white">{report.final_verdict.rating}</strong>
              </span>
            </div>
            <p className="mt-4 text-sm text-slate-300">
              {report.final_verdict.why_dimensions_align}
            </p>
            <p className="mt-2 text-sm text-amber-200/90">
              Conflicts: {report.final_verdict.conflicts}
            </p>
          </section>

          {/* Risks */}
          <section className="rounded-2xl border border-slate-700/80 bg-slate-900/40 p-6">
            <h2 className="text-lg font-semibold text-white">Risk assessment</h2>
            <ul className="mt-3 list-inside list-disc space-y-1 text-slate-300">
              {report.risk_assessment.key_risks.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-slate-600/80 p-4">
                <p className="text-xs font-medium uppercase text-slate-500">If you own</p>
                <p className="mt-2 text-sm text-slate-300">
                  {report.risk_assessment.action_plan.if_you_own}
                </p>
              </div>
              <div className="rounded-lg border border-slate-600/80 p-4">
                <p className="text-xs font-medium uppercase text-slate-500">
                  If you want to buy
                </p>
                <p className="mt-2 text-sm text-slate-300">
                  {report.risk_assessment.action_plan.if_you_want_to_buy}
                </p>
              </div>
            </div>
          </section>

          {/* Citations */}
          <section className="rounded-2xl border border-slate-700/80 bg-slate-900/40 p-6">
            <h2 className="text-lg font-semibold text-white">Citations</h2>
            <p className="mt-1 text-sm text-slate-500">
              Placeholder sources for Phase 1 — RAG will populate these with retrieved chunks.
            </p>
            <ul className="mt-4 space-y-4">
              {report.citations.map((c) => (
                <li
                  key={c.id}
                  className="rounded-lg border border-slate-700 bg-slate-950/50 p-4 text-sm"
                >
                  <p className="font-medium text-slate-200">{c.title}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    {c.source}
                    {c.date ? ` · ${c.date}` : ""}
                  </p>
                  {c.url && (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-block text-xs text-emerald-400 hover:underline"
                    >
                      {c.url}
                    </a>
                  )}
                  {c.snippet && <p className="mt-2 text-slate-400">{c.snippet}</p>}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
