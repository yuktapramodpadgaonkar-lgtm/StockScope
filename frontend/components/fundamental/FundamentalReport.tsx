"use client";

import { useCallback, useEffect, useState } from "react";

import { SectionCard } from "@/components/fundamental/SectionCard";
import { VerdictBadge } from "@/components/fundamental/VerdictBadge";
import { Card } from "@/components/ui/Card";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { MetricCard } from "@/components/ui/MetricCard";
import {
  fetchFundamentalAnalysis,
  type FundamentalAnalysisResponse,
} from "@/lib/fundamental-api";

function formatCap(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  if (n >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  return n.toLocaleString();
}

function formatPrice(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return `${n.toFixed(2)}%`;
}

function formatNum(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

type FundamentalReportProps = {
  /** Optional initial ticker text (does not fetch until Analyze). */
  defaultTicker?: string;
};

export function FundamentalReport({ defaultTicker = "" }: FundamentalReportProps) {
  const [input, setInput] = useState(defaultTicker);
  const [llmChoice, setLlmChoice] = useState<"mistral" | "llama" | "gemini">("mistral");
  const [includeRag, setIncludeRag] = useState(true);
  const [report, setReport] = useState<FundamentalAnalysisResponse | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (symbol: string) => {
    const sym = symbol.trim();
    if (!sym) {
      setError("Enter a ticker symbol.");
      return;
    }
    setHasSearched(true);
    const selected = llmChoice;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFundamentalAnalysis(sym, {
        includeLlm: true,
        includeRag,
        preferredModel: selected,
      });
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : "Failed to load fundamental analysis");
    } finally {
      setLoading(false);
    }
  }, [llmChoice, includeRag]);

  useEffect(() => {
    setInput(defaultTicker);
  }, [defaultTicker]);

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex min-w-[220px] flex-1 flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Ticker</span>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value.toUpperCase())}
              onKeyDown={(e) => {
                if (e.key === "Enter") void load(input);
              }}
              placeholder="Select or enter a stock ticker (e.g. AAPL)"
              className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 font-mono text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
              autoComplete="off"
              spellCheck={false}
            />
          </label>
          <button
            type="button"
            onClick={() => void load(input)}
            disabled={loading}
            className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-60"
          >
            {loading ? "Analyzing..." : "Analyze"}
          </button>
        </div>
        <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start">
          <label className="flex max-w-md flex-1 flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">AI model</span>
            <select
              value={llmChoice}
              onChange={(e) => setLlmChoice(e.target.value as "mistral" | "llama" | "gemini")}
              className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-slate-200"
            >
              <option value="gemini">Gemini</option>
              <option value="mistral">Mistral</option>
              <option value="llama">Llama 3.1</option>
            </select>
            <span className="text-xs text-slate-500">
              Each run requests an AI explanation from the selected provider; metrics stay deterministic.
            </span>
          </label>
          <label className="flex cursor-pointer items-start gap-2 rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2.5 text-sm text-slate-800">
            <input
              type="checkbox"
              checked={includeRag}
              onChange={(e) => setIncludeRag(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
            />
            <span>
              <span className="font-medium text-slate-900">Include SEC filing context</span>
              <span className="mt-0.5 block text-xs font-normal text-slate-500">
                Runs hybrid retrieval over ingested 10-K/10-Q/8-K excerpts when SEC EDGAR is configured in the backend.
              </span>
            </span>
          </label>
        </div>
      </Card>

      {error && (
        <Card className="border-rose-200 bg-rose-50">
          <p className="text-sm font-medium text-rose-800">Could not load report</p>
          <p className="mt-1 text-sm text-rose-700">{error}</p>
        </Card>
      )}

      {loading && !report && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <Card key={i} className="p-4">
              <LoadingSkeleton className="h-4 w-24" />
              <LoadingSkeleton className="mt-3 h-7 w-28" />
            </Card>
          ))}
        </div>
      )}

      {!loading && !report && !error && !hasSearched && (
        <Card className="text-center">
          <p className="text-sm text-slate-600">
            Enter a ticker symbol and click <span className="font-medium text-slate-800">Analyze</span> to load a
            fundamental health report.
          </p>
        </Card>
      )}

      {report && (
        <div className="space-y-6">
          {loading && (
            <p className="text-center text-xs text-slate-500">Updating analysis…</p>
          )}

          <Card>
            <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
              <div>
                <p className="font-mono text-sm font-semibold text-slate-600">{report.ticker}</p>
                <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900">
                  {report.company_name}
                </h2>
              </div>
              {report.current_price != null && (
                <p className="text-3xl font-semibold tabular-nums text-slate-900">
                  {formatPrice(report.current_price)}
                </p>
              )}
            </div>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <dt className="text-slate-500">Sector</dt>
                <dd className="text-slate-800">{report.sector}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Industry</dt>
                <dd className="text-slate-800">{report.industry}</dd>
              </div>
              <div className="flex items-center sm:justify-end lg:justify-start">
                <VerdictBadge verdict={report.verdict} />
              </div>
            </dl>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="transition-transform duration-150 hover:-translate-y-0.5">
              <MetricCard label="Market Cap" value={formatCap(report.metrics.market_cap)} />
            </div>
            <div className="transition-transform duration-150 hover:-translate-y-0.5">
              <MetricCard label="P/E Ratio" value={formatNum(report.metrics.trailing_pe)} />
            </div>
            <div className="transition-transform duration-150 hover:-translate-y-0.5">
              <MetricCard label="EPS" value={formatNum(report.metrics.earnings_growth_yoy_pct)} subtext="YoY growth proxy" />
            </div>
            <div className="transition-transform duration-150 hover:-translate-y-0.5">
              <MetricCard label="Revenue" value={formatPct(report.metrics.revenue_growth_yoy_pct)} subtext="YoY growth" />
            </div>
            <div className="transition-transform duration-150 hover:-translate-y-0.5">
              <MetricCard label="Profit Margin" value={formatPct(report.metrics.profit_margin_pct)} />
            </div>
            <div className="transition-transform duration-150 hover:-translate-y-0.5">
              <MetricCard label="Debt/Equity" value={formatNum(report.metrics.debt_to_equity)} />
            </div>
            <div className="transition-transform duration-150 hover:-translate-y-0.5">
              <MetricCard label="Beta" value="—" subtext="Not available in current API payload" />
            </div>
            <div className="transition-transform duration-150 hover:-translate-y-0.5">
              <MetricCard label="Dividend Yield" value={formatPct(report.metrics.dividend_yield_pct)} />
            </div>
          </div>

          <SectionCard
            title="Financial Health Summary"
            subtitle="Blended view from valuation, profitability, leverage, and growth snapshots."
          >
            <div className="grid gap-3 text-sm text-slate-700 sm:grid-cols-2 lg:grid-cols-3">
              <p>
                <span className="font-medium text-slate-900">Forward P/E:</span>{" "}
                <span className="tabular-nums">{formatNum(report.metrics.forward_pe)}</span>
              </p>
              <p>
                <span className="font-medium text-slate-900">Operating Margin:</span>{" "}
                <span className="tabular-nums">{formatPct(report.metrics.operating_margin_pct)}</span>
              </p>
              <p>
                <span className="font-medium text-slate-900">ROE:</span>{" "}
                <span className="tabular-nums">{formatPct(report.metrics.roe_pct)}</span>
              </p>
              <p>
                <span className="font-medium text-slate-900">Current Ratio:</span>{" "}
                <span className="tabular-nums">{formatNum(report.metrics.current_ratio)}</span>
              </p>
              <p>
                <span className="font-medium text-slate-900">Earnings Growth:</span>{" "}
                <span className="tabular-nums">{formatPct(report.metrics.earnings_growth_yoy_pct)}</span>
              </p>
            </div>
          </SectionCard>

          <div className="grid gap-6 lg:grid-cols-2">
            <SectionCard title="Strengths" className="border-emerald-200 bg-emerald-50/60">
              <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-slate-800">
                {report.strengths.map((s, i) => (
                  <li key={`strength-${i}`}>{s}</li>
                ))}
              </ul>
            </SectionCard>
            <SectionCard title="Risks" className="border-amber-200 bg-amber-50/60">
              <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-slate-800">
                {report.risks.map((r, i) => (
                  <li key={`risk-${i}`}>{r}</li>
                ))}
              </ul>
            </SectionCard>
          </div>

          {(Array.isArray(report.rag_evidence) || report.rag_error) && (
            <SectionCard
              title="SEC filing context (RAG)"
              subtitle="Retrieved excerpts from recent filings when backend SEC ingest is enabled."
              className="border-sky-200 bg-sky-50/50"
            >
              {report.rag_error ? (
                <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" role="status">
                  {report.rag_error}
                </p>
              ) : null}
              {report.rag_evidence && report.rag_evidence.length > 0 ? (
                <ul className="mt-3 space-y-3">
                  {report.rag_evidence.map((ev, i) => (
                    <li
                      key={ev.chunk_id ?? `ev-${i}`}
                      className="rounded-lg border border-slate-200 bg-white/80 p-3 text-sm text-slate-800"
                    >
                      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                        <span className="font-medium text-slate-900">{ev.title ?? "Filing excerpt"}</span>
                        {ev.section_key ? (
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-slate-600">
                            {ev.section_key}
                          </span>
                        ) : null}
                        {ev.retrieval_score != null ? (
                          <span className="text-xs tabular-nums text-slate-500">score {ev.retrieval_score}</span>
                        ) : null}
                      </div>
                      {ev.url ? (
                        <a
                          href={ev.url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-block text-xs text-teal-700 hover:underline"
                        >
                          Source link
                        </a>
                      ) : null}
                      <p className="mt-2 text-xs leading-relaxed text-slate-600">{ev.text_preview}</p>
                    </li>
                  ))}
                </ul>
              ) : !report.rag_error ? (
                <p className="text-sm text-slate-600">
                  No filing chunks returned (SEC may be disabled or no recent items for this ticker). Metrics and AI text
                  still use yfinance rules.
                </p>
              ) : null}
            </SectionCard>
          )}

          {(report.ai_summary || report.ai_error) && (
            <SectionCard
              title="AI explanation"
              subtitle="Plain-language notes based only on the metrics above—not investment advice."
              className="border-violet-200 bg-violet-50/50"
            >
              {report.ai_error && (
                <p
                  className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
                  role="status"
                >
                  {report.ai_error}
                </p>
              )}
              {report.ai_summary && (
                <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
                  {report.ai_summary}
                </div>
              )}
              {report.ai_model && (
                <p className="mt-3 text-xs text-slate-500">Model: {report.ai_model}</p>
              )}
            </SectionCard>
          )}

          <SectionCard title="Final Verdict" subtitle="High-level signal from current fundamental scoring.">
            <div className="flex flex-wrap items-center gap-3">
              <VerdictBadge verdict={report.verdict} />
              <p className="text-sm text-slate-700">{report.verdict}</p>
            </div>
          </SectionCard>

          <SectionCard
            title="Citations / Data Sources"
            subtitle="Current fundamentals are sourced from backend provider snapshots (yfinance)."
          >
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
              <li>Market data provider configured in backend settings</li>
              <li>Server-side fundamental service computes strengths/risks/verdict</li>
              <li>Ticker lookup: {report.ticker}</li>
            </ul>
            <p className="mt-4 text-xs leading-relaxed text-slate-500">{report.disclaimer}</p>
          </SectionCard>
        </div>
      )}
    </div>
  );
}
