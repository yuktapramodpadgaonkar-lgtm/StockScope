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
  type ScoreSignal,
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

function Term({
  label,
  fullForm,
  definition,
}: {
  label: string;
  fullForm: string;
  definition: string;
}) {
  return (
    <span
      className="cursor-help underline decoration-dotted underline-offset-2"
      title={`${fullForm}: ${definition}`}
      aria-label={`${label}: ${fullForm}. ${definition}`}
    >
      {label}
    </span>
  );
}

function ProvenanceAside({ tag, detail }: { tag: string; detail: string }) {
  return (
    <aside className="mb-4 rounded-lg border border-dashed border-slate-300 bg-white/80 px-3 py-2 text-[11px] leading-snug text-slate-600">
      <span className="font-mono font-semibold uppercase tracking-wide text-slate-500">{tag}</span>
      {" — "}
      {detail}
    </aside>
  );
}

function AiGenerationBlock({
  heading,
  modelLabel,
  children,
}: {
  heading?: string;
  modelLabel?: string | null;
  children: string;
}) {
  const body = children.trim();
  if (!body) return null;
  return (
    <div className="relative mt-4 overflow-hidden rounded-xl border border-blue-200 bg-blue-50/70 px-4 py-4 text-blue-950 shadow-sm">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-blue-900">
          AI-generated
        </span>
        {modelLabel ? (
          <span className="text-[10px] font-semibold uppercase tracking-wide text-blue-800">
            via {modelLabel}
          </span>
        ) : null}
      </div>
      {heading ? <p className="mb-2 text-[11px] font-semibold text-blue-900">{heading}</p> : null}
      <p className="whitespace-pre-wrap text-sm italic leading-relaxed text-blue-900">{body}</p>
    </div>
  );
}

const BS_PHASES = ["Fetching data…", "Scoring…", "Writing explanation…"];
const BS_PHASE_DELAYS = [0, 4000, 10000];

export function BuySellReportView() {
  const [ticker, setTicker] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [llmChoice, setLlmChoice] = useState<BuySellModelChoice>("hf_qwen");
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

  const dimensionSignals = useMemo(() => {
    const empty = {
      fundamental: { pos: [] as ScoreSignal[], neg: [] as ScoreSignal[] },
      technical: { pos: [] as ScoreSignal[], neg: [] as ScoreSignal[] },
      sentiment: { pos: [] as ScoreSignal[], neg: [] as ScoreSignal[] },
    };
    const rs = report?.scoring_engine?.rule_scores;
    if (!rs) return empty;
    const split = (signals: ScoreSignal[]) => ({
      pos: signals.filter((s) => s.points > 0).slice(0, 3),
      neg: signals.filter((s) => s.points < 0).slice(0, 3),
    });
    return {
      fundamental: split(rs.fundamental.signals || []),
      technical: split(rs.technical.signals || []),
      sentiment: split(rs.sentiment.signals || []),
    };
  }, [report]);

  const downloadReport = useCallback(() => {
    if (!report) return;
    const contradictionLines: string[] = [
      report.final_verdict.conflicts,
      ...(report.agent_pipeline?.critic.flags ?? []),
      ...(report.agent_pipeline?.critic.notes ?? []),
      ...(report.llm_review?.warnings ?? []),
    ].filter(Boolean);
    const content = [
      `StockScope Buy/Sell Analysis Report`,
      `Ticker: ${report.ticker}`,
      `Recommendation: ${report.recommendation}`,
      `Overall Score: ${report.final_verdict.overall_score}`,
      `Confidence: ${report.confidence}`,
      `Setup Quality: ${report.setup_quality}`,
      "",
      "Deterministic Ratings",
      `- Fundamental: ${report.fundamental_analysis.score} (weight ${report.fundamental_analysis.weight}%)`,
      `- Technical: ${report.technical_analysis.score} (weight ${report.technical_analysis.weight}%)`,
      `- Sentiment: ${report.sentiment_analysis.score} (weight ${report.sentiment_analysis.weight}%)`,
      `- Deterministic thesis: ${report.investment_thesis.summary}`,
      "",
      "Potential Contradictions / Failure Risks",
      ...(contradictionLines.length ? contradictionLines.map((x) => `- ${x}`) : ["- None highlighted in this run."]),
      "",
      "AI Explanation",
      `- Requested model: ${llmChoice}`,
      `- Resolved model: ${report.llm_review?.model ?? "none"}`,
      report.llm_review?.rationale ? report.llm_review.rationale : "LLM review unavailable.",
      "",
      "AI structured narratives (multi-section LLM)",
      ...(report.ai_narratives
        ? [
            `- Model used: ${report.ai_narratives.model_used}`,
            "",
            "--- Thesis expansion ---",
            report.ai_narratives.thesis_expansion,
            "",
            "--- Fundamentals explained ---",
            report.ai_narratives.fundamentals_explained,
            "",
            "--- Technical explained ---",
            report.ai_narratives.technical_explained,
            "",
            "--- Sentiment explained ---",
            report.ai_narratives.sentiment_explained,
            "",
            "--- Final synthesis (AI) ---",
            report.ai_narratives.final_synthesis_ai,
            "",
            "--- Risk commentary (AI) ---",
            report.ai_narratives.risk_commentary_ai,
          ]
        : ["- Not populated for this run (LLM disabled, empty response, or provider error)."]),
      "",
      "Citations",
      ...report.citations.map((c) => `- ${c.title} | ${c.source}${c.url ? ` | ${c.url}` : ""}`),
      "",
      "Disclaimer",
      report.disclaimer,
    ].join("\n");
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.ticker}_buy_sell_report.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [report, llmChoice, includeLlmReview]);

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
                    <option value="hf_qwen">Qwen 2.5 1.5B Instruct (HF)</option>
                    <option value="hf_mistral_instruct">Mistral 7B Instruct v0.3 (HF)</option>
                    <option value="finbert">FinBERT narrative + RAG</option>
                    <option value="gemini">Gemini</option>
                    <option value="llama">Llama 3.1 (Ollama)</option>
                    <option value="mistral">Mistral 7B (Ollama)</option>
                  </select>
                  <p className="mt-1 max-w-xs text-[10px] leading-snug text-slate-500">
                    Default <span className="font-mono">hf_qwen</span> hits Hugging Face Inference (needs{" "}
                    <span className="font-mono">HUGGINGFACE_API_TOKEN</span>).{" "}
                    <span className="font-mono">finbert</span> builds a label+RAG summary (no generative HF instruct).{" "}
                    Gemini / Ollama use their usual keys locally or in <span className="font-mono">.env</span>.
                  </p>
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
                <button
                  type="button"
                  onClick={downloadReport}
                  disabled={!report}
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-50"
                >
                  Download report
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

            <Card className="border-slate-200 bg-white">
              <h2 className="text-lg font-semibold text-slate-900">How to read this report</h2>
              <p className="mt-1 text-sm text-slate-600">
                StockScope separates fixed rule outputs from model-written commentary so you always know what is repeatable
                versus interpretive.
              </p>
              <dl className="mt-4 grid gap-3 text-[11px] leading-snug text-slate-600 sm:grid-cols-2">
                <div className="rounded-lg border border-slate-100 bg-slate-50/80 p-3">
                  <dt className="font-mono font-semibold uppercase tracking-wide text-slate-700">Deterministic slate</dt>
                  <dd className="mt-1">
                    Scores, drivers, valuations, RSI/MACD/MA fields, citations list, conflicts string, critic flags, and agent
                    trace come from the scoring engine and tooling — same inputs yields the same numbers.
                  </dd>
                </div>
                <div className="rounded-lg border border-blue-100 bg-blue-50/40 p-3">
                  <dt className="font-mono font-semibold uppercase tracking-wide text-blue-900">AI narration</dt>
                  <dd className="mt-1 text-blue-950/90">
                    Blue italic blocks are written by your selected backend (HF instruct, Gemini, Ollama…) in a structured
                    JSON pass. They explain what metrics usually mean — they never replace or alter the deterministic
                    recommendation.
                  </dd>
                </div>
                <div className="rounded-lg border border-violet-100 bg-violet-50/30 p-3">
                  <dt className="font-mono font-semibold uppercase tracking-wide text-violet-900">Agent pipeline</dt>
                  <dd className="mt-1">
                    Shows planner + executor timings when agents are enabled. It documents how Layer1 / RAG / scoring steps ran,
                    not a second opinion from a trading model.
                  </dd>
                </div>
                <div className="rounded-lg border border-sky-100 bg-sky-50/30 p-3">
                  <dt className="font-mono font-semibold uppercase tracking-wide text-sky-900">Session memory</dt>
                  <dd className="mt-1">
                    Echo of your session id / recent tickers / horizon hints for UX follow-ups — not an extra signal in the math.
                  </dd>
                </div>
              </dl>
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
              <ProvenanceAside
                tag="deterministic thesis"
                detail="Deterministic pillar summary plus rule-counted drivers. Model expansion below teaches how to read those drivers inside the mosaic."
              />
              <h2 className="text-xl font-semibold text-slate-900">Investment thesis</h2>
              <p className="mt-3 text-base leading-relaxed text-slate-700">{report.investment_thesis.summary}</p>
              {report.investment_thesis.key_drivers.length > 0 && (
                <ul className="mt-4 space-y-2 border-t border-slate-100 pt-4 text-sm text-slate-700">
                  {report.investment_thesis.key_drivers.map((d) => (
                    <li key={d} className="flex gap-2">
                      <span className="text-slate-400" aria-hidden>
                        ▸
                      </span>
                      <span>{d}</span>
                    </li>
                  ))}
                </ul>
              )}
              {report.ai_narratives?.thesis_expansion ? (
                <AiGenerationBlock
                  modelLabel={report.ai_narratives.model_used}
                  heading="LLM expands how this mosaic fits together (education)."
                >
                  {report.ai_narratives.thesis_expansion}
                </AiGenerationBlock>
              ) : null}
            </Card>

            {report.scoring_engine && (
              <Card className="border-indigo-200 bg-indigo-50/30">
                <h2 className="text-xl font-semibold text-slate-900">Dimensional signal breakdown</h2>
                <p className="mt-1 text-sm text-slate-600">
                  Top positive and negative deterministic signals used to calculate each dimension score.
                </p>
                <div className="mt-4 grid gap-4 lg:grid-cols-3">
                  {(
                    [
                      ["Fundamental", dimensionSignals.fundamental],
                      ["Technical", dimensionSignals.technical],
                      ["Sentiment", dimensionSignals.sentiment],
                    ] as const
                  ).map(([name, grp]) => (
                    <Card key={name} className="border-slate-200 bg-white/90 p-4">
                      <p className="text-sm font-semibold text-slate-900">{name}</p>
                      <p className="mt-2 text-xs font-semibold uppercase text-emerald-700">Positive signals</p>
                      <ul className="mt-1 space-y-1 text-xs text-slate-700">
                        {grp.pos.length > 0 ? grp.pos.map((s) => (
                          <li key={`${name}-pos-${s.name}`}>+{s.points}: {s.reason}</li>
                        )) : <li>None</li>}
                      </ul>
                      <p className="mt-3 text-xs font-semibold uppercase text-rose-700">Negative signals</p>
                      <ul className="mt-1 space-y-1 text-xs text-slate-700">
                        {grp.neg.length > 0 ? grp.neg.map((s) => (
                          <li key={`${name}-neg-${s.name}`}>{s.points}: {s.reason}</li>
                        )) : <li>None</li>}
                      </ul>
                    </Card>
                  ))}
                </div>
              </Card>
            )}

            {/* Three pillars */}
            <div className="grid gap-6 lg:grid-cols-3">
              <Card>
                <ProvenanceAside
                  tag="pillar · fundamentals"
                  detail="Growth, leverage, profitability, and valuation knobs from Layer1 snapshots — scored deterministically."
                />
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Fundamentals ({report.fundamental_analysis.weight}%)
                </h3>
                <div className="mt-4">{scoreBar("Score", report.fundamental_analysis.score)}</div>
                <p className="mt-4 text-sm leading-relaxed text-slate-700">
                  {report.fundamental_analysis.business_performance}
                </p>
                <dl className="mt-4 space-y-2 border-t border-slate-100 pt-4 text-xs text-slate-500">
                  <div className="flex justify-between gap-2">
                    <dt>
                      <Term
                        label="P/E"
                        fullForm="Price-to-Earnings Ratio"
                        definition="How much investors are paying for each one dollar of annual earnings."
                      />
                    </dt>
                    <dd className="tabular-nums text-slate-800">
                      {report.fundamental_analysis.valuation_analysis.pe ?? "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-2">
                    <dt>
                      <Term
                        label="DCF value"
                        fullForm="Discounted Cash Flow Value"
                        definition="Estimated fair value based on projected future cash flows discounted to today."
                      />
                    </dt>
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
                {report.ai_narratives?.fundamentals_explained ? (
                  <AiGenerationBlock
                    modelLabel={report.ai_narratives.model_used}
                    heading="What fundamental metrics imply here (education)."
                  >
                    {report.ai_narratives.fundamentals_explained}
                  </AiGenerationBlock>
                ) : null}
              </Card>

              <Card>
                <ProvenanceAside
                  tag="pillar · technicals"
                  detail="Momentum and moving-average cues computed locally — independent of brokerage charting UI."
                />
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Technicals ({report.technical_analysis.weight}%)
                </h3>
                <div className="mt-4">{scoreBar("Score", report.technical_analysis.score)}</div>
                <p className="mt-4 text-sm leading-relaxed text-slate-700">
                  {report.technical_analysis.trend_analysis}
                </p>
                <dl className="mt-4 space-y-1.5 border-t border-slate-100 pt-4 text-xs text-slate-600">
                  <div>
                    <Term
                      label="RSI"
                      fullForm="Relative Strength Index"
                      definition="Momentum indicator from 0 to 100; higher values mean stronger recent buying pressure."
                    />
                    : {report.technical_analysis.indicators.rsi ?? "—"}
                  </div>
                  <div>
                    <Term
                      label="MACD"
                      fullForm="Moving Average Convergence Divergence"
                      definition="Trend and momentum indicator comparing fast and slow moving averages."
                    />
                    : {report.technical_analysis.indicators.macd_signal || "—"}
                  </div>
                  <div>
                    <Term
                      label="MA 50"
                      fullForm="50-day Moving Average"
                      definition="Average closing price over the last 50 trading days."
                    />
                    : {report.technical_analysis.indicators.ma_50 ?? "—"}
                  </div>
                  <div>
                    <Term
                      label="MA 200"
                      fullForm="200-day Moving Average"
                      definition="Average closing price over the last 200 trading days, often used for long-term trend."
                    />
                    : {report.technical_analysis.indicators.ma_200 ?? "—"}
                  </div>
                  <div>Price vs MA: {report.technical_analysis.indicators.price_vs_ma || "—"}</div>
                </dl>
                {report.ai_narratives?.technical_explained ? (
                  <AiGenerationBlock
                    modelLabel={report.ai_narratives.model_used}
                    heading="Technical indicators unpacked (education)."
                  >
                    {report.ai_narratives.technical_explained}
                  </AiGenerationBlock>
                ) : null}
              </Card>

              <Card>
                <ProvenanceAside
                  tag="pillar · sentiment"
                  detail="Titles pulled from headline feeds plus FinBERT/keyword tagging when configured — complements but does not override fundamentals/technicals."
                />
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
                {report.ai_narratives?.sentiment_explained ? (
                  <AiGenerationBlock
                    modelLabel={report.ai_narratives.model_used}
                    heading="How to read headline sentiment stacks (education)."
                  >
                    {report.ai_narratives.sentiment_explained}
                  </AiGenerationBlock>
                ) : null}
              </Card>
            </div>

            {/* Final synthesis */}
            <Card className="border-slate-200 bg-white shadow-sm">
              <ProvenanceAside
                tag="synthesis · core"
                detail="Weighted rule blend produces the headline rating; conflicts string lists dispersion / data gaps surfaced by deterministic heuristics."
              />
              <h2 className="text-xl font-semibold text-slate-900">Final synthesis</h2>
              <div className="mt-4 max-w-xl">{scoreBar("Overall score", report.final_verdict.overall_score)}</div>
              <p className="mt-5 text-base leading-relaxed text-slate-700">
                {report.final_verdict.why_dimensions_align}
              </p>
              <p className="mt-3 text-sm font-medium text-amber-800">
                Conflicts: {report.final_verdict.conflicts}
              </p>
              {report.ai_narratives?.final_synthesis_ai ? (
                <AiGenerationBlock
                  modelLabel={report.ai_narratives.model_used}
                  heading="Deeper mosaic view from the structured LLM pass (education)."
                >
                  {report.ai_narratives.final_synthesis_ai}
                </AiGenerationBlock>
              ) : null}
            </Card>

            {report.agent_pipeline?.critic && (
              <Card className="border-amber-200 bg-amber-50/40">
                <ProvenanceAside
                  tag="conflicts · quality"
                  detail="Planner critic + rule-based dispersion checks validate evidence completeness — advisory only and separate from BUY/HOLD/SELL math."
                />
                <h2 className="text-xl font-semibold text-slate-900">Conflict & quality checks</h2>
                <p className="mt-2 text-sm text-slate-700">
                  Critic status: {report.agent_pipeline.critic.passed ? "passed" : "review recommended"}.
                </p>
                {report.agent_pipeline.critic.flags.length > 0 && (
                  <ul className="mt-3 list-inside list-disc text-sm text-amber-900">
                    {report.agent_pipeline.critic.flags.map((f) => (
                      <li key={`flag-${f}`}>{f}</li>
                    ))}
                  </ul>
                )}
                {report.agent_pipeline.critic.notes.length > 0 && (
                  <ul className="mt-2 list-inside list-disc text-sm text-slate-700">
                    {report.agent_pipeline.critic.notes.map((n) => (
                      <li key={`note-${n}`}>{n}</li>
                    ))}
                  </ul>
                )}
              </Card>
            )}

            {report.llm_review && (
              <Card className="border-violet-200 bg-violet-50/50">
                <ProvenanceAside
                  tag="AI explanation"
                  detail="Standalone prose pass that narrates deterministic scores (FinBERT labeling path when selected vs generative backends). Separate from the blue structured narrative blocks; both obey the educational safety charter."
                />
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
                <div className="mt-2 whitespace-pre-wrap text-sm italic leading-relaxed text-blue-900">
                  {report.llm_review.rationale}
                </div>
                <p className="mt-1 text-[11px] text-blue-800/90">
                  Styled in blue italic to match other generative narration in this workspace.
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
              <ProvenanceAside
                tag="risk · scaffolding"
                detail="Starter risk bullets + playbook language come from deterministic templates for every run."
              />
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
              {report.ai_narratives?.risk_commentary_ai ? (
                <AiGenerationBlock
                  modelLabel={report.ai_narratives.model_used}
                  heading="Scenario commentary from the structured narrative pass."
                >
                  {report.ai_narratives.risk_commentary_ai}
                </AiGenerationBlock>
              ) : includeLlmReview ? (
                <p className="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                  Structured narrative risk commentary was not returned (provider disabled or token missing). Try another
                  model or check server logs — deterministic checklist above still applies.
                </p>
              ) : null}
            </Card>

            {/* Citations */}
            <Card>
              <ProvenanceAside
                tag="citations"
                detail="Structured provenance IDs for Layer1 plus optional Hybrid RAG chunk ids when retrieval is toggled."
              />
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
                <ProvenanceAside
                  tag="session memory · phase 7"
                  detail="Hydrated after analyze for continuity — not fused into deterministic weights."
                />
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
                <ProvenanceAside
                  tag="agent pipeline · phase 6"
                  detail="Operational trace tying Layer1 ingestion, retrieval toggles, and scoring steps together for auditability."
                />
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
