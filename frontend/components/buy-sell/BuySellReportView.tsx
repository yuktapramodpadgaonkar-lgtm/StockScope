"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { MetricCard } from "@/components/ui/MetricCard";
import { SectionHeader } from "@/components/ui/SectionHeader";
import {
  fetchBuySellReport,
  type BuySellModelChoice,
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

const BS_PHASES = ["Fetching data…", "Scoring…", "Writing explanation…"];
const BS_PHASE_DELAYS = [0, 4000, 10000];

export function BuySellReportView() {
  const [ticker, setTicker] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [llmChoice, setLlmChoice] = useState<BuySellModelChoice>("gemini");
  const [includeLlmReview, setIncludeLlmReview] = useState(true);
  const [includeRetrieval, setIncludeRetrieval] = useState(false);
  const [report, setReport] = useState<BuySellReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  function startPhaseTimers() {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
    BS_PHASE_DELAYS.forEach((delay, idx) => {
      timersRef.current.push(setTimeout(() => setPhaseIdx(idx), delay));
    });
  }

  function clearPhaseTimers() {
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];
  }

  useEffect(() => () => clearPhaseTimers(), []);

  const load = useCallback(async (sym: string) => {
    const normalized = sym.trim().toUpperCase();
    if (!normalized) {
      setError("Enter a ticker symbol.");
      return;
    }
    setHasSearched(true);
    setTicker(normalized);
    setLoading(true);
    setPhaseIdx(0);
    setError(null);
    startPhaseTimers();
    try {
      const data = await fetchBuySellReport(normalized, {
        includeLlmReview,
        includeRetrieval,
        useAgentPipeline: true,
        preferredModel: llmChoice,
      });
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : "Failed to load report");
    } finally {
      clearPhaseTimers();
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [includeLlmReview, includeRetrieval, llmChoice]);

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

  const citationGroups = useMemo(() => {
    if (!report) {
      return { layer1: [] as BuySellReport["citations"], rag: [] as BuySellReport["citations"] };
    }
    const layer1 = report.citations.filter((c) => c.id.startsWith("layer1-"));
    const rag = report.citations.filter((c) => !c.id.startsWith("layer1-"));
    return { layer1, rag };
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
                    void load(inputValue);
                  }}
                  className="flex items-end gap-2"
                >
                  <label className="flex min-w-[130px] flex-col gap-1">
                    <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">Ticker</span>
                    <input
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value.toUpperCase())}
                      placeholder="AAPL"
                      maxLength={10}
                      className="w-28 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-mono font-semibold text-slate-900 outline-none focus:ring-2 focus:ring-slate-400"
                    />
                  </label>
                </form>
                <label className="flex min-w-[170px] flex-col gap-1">
                  <span className="text-[11px] font-medium uppercase tracking-wide text-slate-500">AI model</span>
                  <select
                    value={llmChoice}
                    onChange={(e) => setLlmChoice(e.target.value as BuySellModelChoice)}
                    className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-slate-200"
                  >
                    <option value="gemini">Gemini</option>
                    <option value="llama">Llama 3.1</option>
                    <option value="mistral">Mistral</option>
                  </select>
                </label>
                <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                  <input
                    type="checkbox"
                    checked={includeLlmReview}
                    onChange={(e) => setIncludeLlmReview(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
                  />
                  Include AI explanation
                </label>
                <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                  <input
                    type="checkbox"
                    checked={includeRetrieval}
                    onChange={(e) => setIncludeRetrieval(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
                  />
                  Include RAG retrieval
                </label>
                <button
                  type="button"
                  onClick={() => void load(inputValue)}
                  disabled={loading || !inputValue.trim()}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
                >
                  {loading ? BS_PHASES[phaseIdx] : "Search"}
                </button>
              </div>
            }
          />
        </Card>

        {loading && !report && (
          <>
            <Card>
              <div className="flex items-center gap-3 px-1 py-2">
                <svg className="h-4 w-4 animate-spin text-slate-500" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span className="text-sm font-medium text-slate-700">{BS_PHASES[phaseIdx]}</span>
              </div>
              <div className="mt-3 flex gap-2">
                {BS_PHASES.map((label, i) => (
                  <div key={label} className="flex-1">
                    <div className={`h-1.5 rounded-full transition-colors duration-500 ${i <= phaseIdx ? "bg-slate-800" : "bg-slate-200"}`} />
                    <p className={`mt-1 text-[10px] ${i <= phaseIdx ? "text-slate-700" : "text-slate-400"}`}>{label}</p>
                  </div>
                ))}
              </div>
            </Card>
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
          </>
        )}

        {!loading && !report && !error && !hasSearched && (
          <Card className="text-center">
            <p className="text-sm text-slate-600">
              Enter a ticker symbol and click <span className="font-medium text-slate-800">Search</span> to run Buy/Sell analysis.
            </p>
          </Card>
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

            {report.llm_review && (
              <Card className="border-violet-200 bg-violet-50/50">
                <h2 className="text-xl font-semibold text-slate-900">AI explanation</h2>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                  <Badge label={`Requested model: ${llmChoice}`} variant="neutral" />
                  <Badge
                    label={
                      report.llm_review.model && report.llm_review.model !== "none"
                        ? `Answered by: ${report.llm_review.model}`
                        : "Answered by: deterministic fallback"
                    }
                    variant={report.llm_review.model && report.llm_review.model !== "none" ? "positive" : "neutral"}
                  />
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                  {report.llm_review.rationale}
                </p>
                {report.llm_review.model === "none" && (
                  <p className="mt-2 text-xs text-amber-700">
                    LLM provider was unavailable, so a deterministic fallback explanation was shown. Set
                    `GEMINI_API_KEY` or run Ollama locally for richer model-generated output.
                  </p>
                )}
              </Card>
            )}

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
                {includeRetrieval
                  ? "Includes Layer1 sources and retrieved chunks when available."
                  : "Showing Layer1 deterministic sources. Turn on 'Include RAG retrieval' to add retrieved evidence chunks."}
              </p>
              <ul className="mt-5 space-y-4">
                {citationGroups.layer1.map((c) => (
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

            <Card className="border-sky-200 bg-sky-50/50">
              <h2 className="text-xl font-semibold text-slate-900">RAG evidence used</h2>
              <p className="mt-1 text-sm text-slate-600">
                Retrieved document/news chunks that were used in Buy/Sell analysis when retrieval is enabled.
              </p>
              {!includeRetrieval && (
                <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                  Retrieval is currently off. Turn on <span className="font-medium">Include RAG retrieval</span> and run
                  Search to attach retrieved evidence.
                </p>
              )}
              {includeRetrieval && citationGroups.rag.length === 0 && (
                <p className="mt-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
                  Retrieval was enabled, but no chunks were returned for this run.
                </p>
              )}
              {citationGroups.rag.length > 0 && (
                <ul className="mt-4 space-y-3">
                  {citationGroups.rag.map((c) => (
                    <li key={c.id} className="rounded-xl border border-sky-100 bg-white/90 p-3 text-sm">
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
                          className="mt-1 inline-block text-xs font-medium text-teal-700 hover:underline"
                        >
                          Source link
                        </a>
                      )}
                      {c.snippet && <p className="mt-2 text-xs leading-relaxed text-slate-600">{c.snippet}</p>}
                    </li>
                  ))}
                </ul>
              )}
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
