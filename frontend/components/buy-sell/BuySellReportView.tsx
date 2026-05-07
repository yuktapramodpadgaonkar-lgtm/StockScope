"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { MetricCard } from "@/components/ui/MetricCard";
import { SectionHeader } from "@/components/ui/SectionHeader";
import {
  fetchBuySellReport,
  type BuySellReport,
  type Recommendation,
} from "@/lib/buy-sell-api";

function scoreBar(label: string, value: number, weight?: number) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs font-medium text-slate-500">
        <span>{label}</span>
        <span className="tabular-nums text-slate-700">
          {value}
          {weight != null ? ` · ${weight}% wt` : ""}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-slate-900 transition-all"
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  );
}

function recommendationBadgeVariant(rec: Recommendation): "buy" | "sell" | "neutral" {
  if (rec === "BUY") return "buy";
  if (rec === "SELL") return "sell";
  return "neutral";
}

function BulletList({ items, tone }: { items: string[]; tone: "bull" | "bear" }) {
  const dot =
    tone === "bull"
      ? "border-emerald-400 bg-emerald-50 text-emerald-700"
      : "border-rose-400 bg-rose-50 text-rose-700";
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">No items in this bucket for this report.</p>;
  }
  return (
    <ul className="space-y-3">
      {items.map((line) => (
        <li key={line} className="flex gap-3 text-sm leading-relaxed text-slate-700">
          <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full border ${dot}`} aria-hidden />
          <span>{line}</span>
        </li>
      ))}
    </ul>
  );
}

export function BuySellReportView() {
  const [ticker, setTicker] = useState("AAPL");
  const [inputValue, setInputValue] = useState("AAPL");
  const [report, setReport] = useState<BuySellReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (sym: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBuySellReport(sym);
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(ticker);
  }, [load, ticker]);

  const bullBear = useMemo(() => {
    if (!report) return { bullish: [] as string[], bearish: [] as string[] };
    const bullish: string[] = [
      ...report.investment_thesis.key_drivers,
      report.fundamental_analysis.verdict,
      report.technical_analysis.verdict,
      report.sentiment_analysis.verdict,
    ].filter(Boolean);
    const bearish: string[] = [
      ...report.risk_assessment.key_risks,
      report.final_verdict.conflicts,
    ].filter(Boolean);
    return { bullish, bearish };
  }, [report]);

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <Card>
          <SectionHeader
            title="Buy / Sell analysis"
            description="Deterministic scoring (fundamentals · technicals · sentiment) with LLM narrative and agent pipeline."
            actions={
              <div className="flex flex-wrap items-center gap-2">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const sym = inputValue.trim().toUpperCase();
                    if (sym) setTicker(sym);
                  }}
                  className="flex gap-1"
                >
                  <input
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value.toUpperCase())}
                    placeholder="AAPL"
                    maxLength={10}
                    className="w-24 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-mono font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-slate-400"
                  />
                  <button
                    type="submit"
                    disabled={loading || !inputValue.trim()}
                    className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
                  >
                    {loading ? "Loading…" : "Analyze"}
                  </button>
                </form>
                <Link
                  href="/"
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                >
                  Home
                </Link>
              </div>
            }
          />
        </Card>

        {loading && !report && (
          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <LoadingSkeleton className="h-40 w-full rounded-2xl" />
            </Card>
            <Card>
              <LoadingSkeleton className="h-40 w-full rounded-2xl" />
            </Card>
            <Card className="lg:col-span-3">
              <LoadingSkeleton className="h-32 w-full rounded-2xl" />
            </Card>
          </div>
        )}

        {error && (
          <Card className="border-rose-200 bg-rose-50">
            <p className="text-sm font-semibold text-rose-800">Could not load report</p>
            <p className="mt-1 text-sm text-rose-700">{error}</p>
          </Card>
        )}

        {report && !loading && (
          <div className="space-y-6">
            <Card className="border-amber-200 bg-amber-50/80">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">Disclaimer</p>
              <p className="mt-2 text-sm text-amber-900/90">{report.disclaimer}</p>
            </Card>

            {/* Hero: score + recommendation */}
            <Card className="overflow-hidden p-0 shadow-md ring-1 ring-slate-200/80">
              <div className="grid gap-6 p-6 lg:grid-cols-[1fr_auto] lg:items-center lg:gap-10">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
                    {report.ticker} · schema {report.schema_version}
                  </p>
                  <div className="mt-4 flex flex-wrap items-end gap-4">
                    <p
                      className="text-6xl font-bold tabular-nums tracking-tight text-slate-900 sm:text-7xl"
                      aria-label={`Overall score ${report.final_verdict.overall_score}`}
                    >
                      {Math.round(report.final_verdict.overall_score)}
                    </p>
                    <div className="pb-2">
                      <p className="text-sm text-slate-500">Composite score</p>
                      <p className="text-sm font-medium text-slate-800">{report.final_verdict.rating}</p>
                    </div>
                  </div>
                  <div className="mt-6 grid gap-3 sm:grid-cols-3">
                    <MetricCard label="Confidence" value={`${report.confidence}`} />
                    <MetricCard label="Setup quality" value={`${report.setup_quality}`} />
                    <MetricCard label="Horizon" value={report.optimal_timeframe} />
                  </div>
                </div>
                <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-slate-200 bg-slate-50/80 px-8 py-10 lg:min-w-[220px]">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Signal</p>
                  <Badge
                    label={report.recommendation}
                    variant={recommendationBadgeVariant(report.recommendation)}
                    className="px-4 py-2 text-sm"
                  />
                  <p className="text-center text-xs text-slate-500">
                    Not investment advice. Scores are model outputs for research.
                  </p>
                </div>
              </div>
            </Card>

            {/* Bullish vs bearish */}
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="border-emerald-100 shadow-sm ring-1 ring-emerald-100/80">
                <h2 className="text-lg font-semibold text-slate-900">Bullish case</h2>
                <p className="mt-1 text-sm text-slate-600">Drivers, pillar verdicts, and constructive read-through.</p>
                <div className="mt-5">
                  <BulletList items={bullBear.bullish} tone="bull" />
                </div>
              </Card>
              <Card className="border-rose-100 shadow-sm ring-1 ring-rose-100/80">
                <h2 className="text-lg font-semibold text-slate-900">Bearish case</h2>
                <p className="mt-1 text-sm text-slate-600">Key risks and stated conflicts across dimensions.</p>
                <div className="mt-5">
                  <BulletList items={bullBear.bearish} tone="bear" />
                </div>
              </Card>
            </div>

            {/* Thesis */}
            <Card>
              <h2 className="text-xl font-semibold text-slate-900">Investment thesis</h2>
              <p className="mt-3 text-base leading-relaxed text-slate-700">{report.investment_thesis.summary}</p>
            </Card>

            {/* Three pillars */}
            <div className="grid gap-6 lg:grid-cols-3">
              <Card>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Fundamentals ({report.fundamental_analysis.weight}%)
                </h3>
                <div className="mt-4">{scoreBar("Score", report.fundamental_analysis.score)}</div>
                <p className="mt-4 text-sm leading-relaxed text-slate-700">
                  {report.fundamental_analysis.business_performance}
                </p>
                <dl className="mt-4 space-y-2 border-t border-slate-100 pt-4 text-xs text-slate-500">
                  <div className="flex justify-between gap-2">
                    <dt>P/E</dt>
                    <dd className="tabular-nums text-slate-800">
                      {report.fundamental_analysis.valuation_analysis.pe ?? "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt>DCF value</dt>
                    <dd className="tabular-nums text-slate-800">
                      {report.fundamental_analysis.valuation_analysis.dcf_value ?? "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt>Price</dt>
                    <dd className="tabular-nums text-slate-800">
                      {report.fundamental_analysis.valuation_analysis.current_price ?? "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt>Implied upside %</dt>
                    <dd className="tabular-nums text-slate-800">
                      {report.fundamental_analysis.valuation_analysis.implied_upside ?? "—"}
                    </dd>
                  </div>
                </dl>
                <p className="mt-3 text-xs text-slate-500">{report.fundamental_analysis.bull_bear_integration}</p>
              </Card>

              <Card>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Technicals ({report.technical_analysis.weight}%)
                </h3>
                <div className="mt-4">{scoreBar("Score", report.technical_analysis.score)}</div>
                <p className="mt-4 text-sm leading-relaxed text-slate-700">
                  {report.technical_analysis.trend_analysis}
                </p>
                <dl className="mt-4 space-y-1.5 border-t border-slate-100 pt-4 text-xs text-slate-600">
                  <div>RSI: {report.technical_analysis.indicators.rsi ?? "—"}</div>
                  <div>MACD: {report.technical_analysis.indicators.macd_signal || "—"}</div>
                  <div>MA 50: {report.technical_analysis.indicators.ma_50 ?? "—"}</div>
                  <div>MA 200: {report.technical_analysis.indicators.ma_200 ?? "—"}</div>
                  <div>Price vs MA: {report.technical_analysis.indicators.price_vs_ma || "—"}</div>
                </dl>
              </Card>

              <Card>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Sentiment ({report.sentiment_analysis.weight}%)
                </h3>
                <div className="mt-4">{scoreBar("Score", report.sentiment_analysis.score)}</div>
                <ul className="mt-4 space-y-2 border-t border-slate-100 pt-4 text-sm text-slate-700">
                  {report.sentiment_analysis.recent_developments.map((line) => (
                    <li key={line} className="border-l-2 border-slate-200 pl-3">
                      {line}
                    </li>
                  ))}
                </ul>
              </Card>
            </div>

            {/* Final synthesis */}
            <Card className="border-slate-200 bg-white shadow-sm">
              <h2 className="text-xl font-semibold text-slate-900">Final synthesis</h2>
              <div className="mt-4 max-w-xl">{scoreBar("Overall score", report.final_verdict.overall_score)}</div>
              <p className="mt-5 text-base leading-relaxed text-slate-700">
                {report.final_verdict.why_dimensions_align}
              </p>
              <p className="mt-3 text-sm font-medium text-amber-800">
                Conflicts: {report.final_verdict.conflicts}
              </p>
            </Card>

            {/* Risk & actions */}
            <Card>
              <h2 className="text-xl font-semibold text-slate-900">Risk assessment</h2>
              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <Card className="border-slate-200 bg-slate-50/80 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">If you own</p>
                  <p className="mt-2 text-sm text-slate-700">{report.risk_assessment.action_plan.if_you_own}</p>
                </Card>
                <Card className="border-slate-200 bg-slate-50/80 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">If you want to buy</p>
                  <p className="mt-2 text-sm text-slate-700">
                    {report.risk_assessment.action_plan.if_you_want_to_buy}
                  </p>
                </Card>
              </div>
            </Card>

            {/* Citations */}
            <Card>
              <h2 className="text-xl font-semibold text-slate-900">Citations</h2>
              <p className="mt-1 text-sm text-slate-500">
                Placeholder sources for Phase 1 — RAG will populate these with retrieved chunks.
              </p>
              <ul className="mt-5 space-y-4">
                {report.citations.map((c) => (
                  <li key={c.id} className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4 text-sm">
                    <p className="font-medium text-slate-900">{c.title}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      {c.source}
                      {c.date ? ` · ${c.date}` : ""}
                    </p>
                    {c.url && (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 inline-block text-xs font-medium text-slate-700 underline-offset-2 hover:underline"
                      >
                        {c.url}
                      </a>
                    )}
                    {c.snippet && <p className="mt-2 text-slate-600">{c.snippet}</p>}
                  </li>
                ))}
              </ul>
            </Card>

            {report.memory && (
              <Card className="border-sky-200 bg-sky-50/50">
                <h2 className="text-xl font-semibold text-slate-900">
                  Session memory <span className="text-xs font-normal text-sky-700">(Phase 7)</span>
                </h2>
                <p className="mt-1 font-mono text-xs text-slate-500">session_id={report.memory.session_id}</p>
                {report.memory.preferred_horizon && (
                  <p className="mt-2 text-sm text-slate-700">Preferred horizon: {report.memory.preferred_horizon}</p>
                )}
                {report.memory.recent_tickers.length > 0 && (
                  <p className="mt-2 text-sm text-slate-700">
                    Recent tickers: {report.memory.recent_tickers.join(", ")}
                  </p>
                )}
                {report.memory.follow_up_context && (
                  <p className="mt-3 text-sm text-slate-600">{report.memory.follow_up_context}</p>
                )}
              </Card>
            )}

            {report.agent_pipeline && (
              <Card className="border-violet-200 bg-violet-50/40">
                <h2 className="text-xl font-semibold text-slate-900">
                  Agent pipeline <span className="text-xs font-normal text-violet-700">(Phase 6)</span>
                </h2>
                <p className="mt-1 text-sm text-slate-600">{report.agent_pipeline.plan_summary}</p>
                <div className="mt-4 flex flex-wrap gap-2 text-sm">
                  <Badge
                    label={report.agent_pipeline.critic.passed ? "Critic: passed" : "Critic: review"}
                    variant={report.agent_pipeline.critic.passed ? "positive" : "neutral"}
                  />
                  {report.agent_pipeline.critic.incomplete_evidence && (
                    <Badge label="Incomplete evidence" variant="negative" />
                  )}
                </div>
                {report.agent_pipeline.critic.flags.length > 0 && (
                  <ul className="mt-3 list-inside list-disc text-sm text-amber-900">
                    {report.agent_pipeline.critic.flags.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                )}
                <details className="mt-4 text-sm text-slate-600">
                  <summary className="cursor-pointer font-medium text-slate-800 hover:text-slate-900">
                    Execution trace ({report.agent_pipeline.execution_trace.length} steps)
                  </summary>
                  <ol className="mt-2 space-y-2 pl-4">
                    {report.agent_pipeline.execution_trace.map((s) => (
                      <li key={`${s.step_id}-${s.duration_ms}`}>
                        <span className="font-mono text-xs text-slate-500">{s.status}</span>{" "}
                        <span className="text-slate-800">{s.step_id}</span>
                        <span className="text-slate-500"> · {s.duration_ms.toFixed(1)} ms</span>
                        {s.detail && <span className="block text-xs text-slate-500">{s.detail}</span>}
                      </li>
                    ))}
                  </ol>
                </details>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
