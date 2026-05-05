"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchFundamentalAnalysis,
  type FundamentalAnalysisResponse,
  type FundamentalMetrics,
} from "@/lib/fundamental-api";

const METRIC_ROWS: { key: keyof FundamentalMetrics; label: string }[] = [
  { key: "market_cap", label: "Market cap" },
  { key: "trailing_pe", label: "Trailing P/E" },
  { key: "forward_pe", label: "Forward P/E" },
  { key: "profit_margin_pct", label: "Profit margin" },
  { key: "operating_margin_pct", label: "Operating margin" },
  { key: "roe_pct", label: "Return on equity" },
  { key: "debt_to_equity", label: "Debt / equity" },
  { key: "current_ratio", label: "Current ratio" },
  { key: "revenue_growth_yoy_pct", label: "Revenue growth (YoY)" },
  { key: "earnings_growth_yoy_pct", label: "Earnings growth (YoY)" },
  { key: "dividend_yield_pct", label: "Dividend yield" },
];

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

function formatMaybePct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return `${n.toFixed(2)}%`;
}

function formatRatio(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatMetricValue(key: keyof FundamentalMetrics, n: number | null): string {
  if (n == null || Number.isNaN(n)) return "—";
  if (key === "market_cap") return formatCap(n);
  if (
    key === "profit_margin_pct" ||
    key === "operating_margin_pct" ||
    key === "roe_pct" ||
    key === "revenue_growth_yoy_pct" ||
    key === "earnings_growth_yoy_pct" ||
    key === "dividend_yield_pct"
  ) {
    return formatMaybePct(n);
  }
  if (key === "trailing_pe" || key === "forward_pe") return formatRatio(n);
  return formatRatio(n);
}

type FundamentalReportProps = {
  /** Initial symbol for the lookup input (loads on mount). */
  defaultTicker?: string;
};

export function FundamentalReport({ defaultTicker = "AAPL" }: FundamentalReportProps) {
  const [input, setInput] = useState(defaultTicker);
  const [llmChoice, setLlmChoice] = useState<"mistral" | "llama" | "gemini">("mistral");
  const llmChoiceRef = useRef(llmChoice);
  llmChoiceRef.current = llmChoice;

  const [report, setReport] = useState<FundamentalAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (symbol: string, choice?: "mistral" | "llama" | "gemini") => {
    const sym = symbol.trim();
    if (!sym) {
      setError("Enter a ticker symbol.");
      return;
    }
    const selected = choice ?? llmChoiceRef.current;
    const provider =
      selected === "gemini" ? "gemini" : "ollama";
    const model =
      selected === "gemini"
        ? "gemini-1.5-flash"
        : selected === "llama"
          ? "llama3.1:8b"
          : "mistral:7b";
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFundamentalAnalysis(sym, true, provider, model);
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : "Failed to load fundamental analysis");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(defaultTicker, llmChoiceRef.current);
  }, [defaultTicker, load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex min-w-[200px] flex-1 flex-col gap-1.5">
          <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Ticker
          </span>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => {
              if (e.key === "Enter") void load(input);
            }}
            placeholder="e.g. AAPL"
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100 outline-none ring-emerald-500/0 transition focus:ring-2 focus:ring-emerald-500/40"
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        <button
          type="button"
          onClick={() => void load(input)}
          disabled={loading}
          className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 shadow-md shadow-emerald-500/15 transition hover:bg-emerald-400 disabled:opacity-60"
        >
          {loading ? "Loading…" : "Analyze"}
        </button>
      </div>

      <label className="flex flex-col gap-1.5 sm:max-w-xs">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
          AI model
        </span>
        <select
          value={llmChoice}
          onChange={(e) => setLlmChoice(e.target.value as "mistral" | "llama" | "gemini")}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:ring-2 focus:ring-emerald-500/40"
        >
          <option value="gemini">Gemini</option>
          <option value="mistral">Mistral</option>
          <option value="llama">Llama 3.1</option>
        </select>
        <p className="text-xs text-slate-500">
          Always requests an AI explanation; deterministic metrics remain the source of truth.
        </p>
      </label>

      {error && (
        <div
          className="rounded-lg border border-rose-500/40 bg-rose-950/40 px-4 py-3 text-sm text-rose-200"
          role="alert"
        >
          <p className="font-medium">Could not load report</p>
          <p className="mt-1 text-rose-200/80">{error}</p>
        </div>
      )}

      {report && !loading && (
        <div className="space-y-6">
          <header className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 shadow-xl backdrop-blur">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
              <div>
                <p className="font-mono text-sm font-semibold text-emerald-400">{report.ticker}</p>
                <h2 className="mt-1 text-xl font-semibold tracking-tight text-white">
                  {report.company_name}
                </h2>
              </div>
              {report.current_price != null && (
                <p className="text-2xl font-semibold tabular-nums text-slate-100">
                  {formatPrice(report.current_price)}
                </p>
              )}
            </div>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-slate-500">Sector</dt>
                <dd className="text-slate-200">{report.sector}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Industry</dt>
                <dd className="text-slate-200">{report.industry}</dd>
              </div>
            </dl>
          </header>

          <section className="rounded-xl border border-slate-800 bg-slate-900/30 p-5 shadow-xl">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Metrics
            </h3>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[320px] text-left text-sm">
                <tbody>
                  {METRIC_ROWS.map(({ key, label }) => (
                    <tr key={key} className="border-b border-slate-800/80 last:border-0">
                      <th className="py-2 pr-4 font-normal text-slate-400">{label}</th>
                      <td className="py-2 text-right font-mono tabular-nums text-slate-100">
                        {formatMetricValue(key, report.metrics[key])}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-5">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-emerald-400/90">
                Strengths
              </h3>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-200">
                {report.strengths.map((s, i) => (
                  <li key={`strength-${i}`}>{s}</li>
                ))}
              </ul>
            </section>
            <section className="rounded-xl border border-amber-500/20 bg-amber-950/15 p-5">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-amber-300/90">
                Risks
              </h3>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-200">
                {report.risks.map((r, i) => (
                  <li key={`risk-${i}`}>{r}</li>
                ))}
              </ul>
            </section>
          </div>

          {(report.ai_summary || report.ai_error) && (
            <section className="rounded-xl border border-violet-500/25 bg-violet-950/20 p-5 shadow-xl">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-violet-300/90">
                AI explanation
              </h3>
              <p className="mt-2 text-xs text-slate-500">
                Plain-language notes from a local model, based only on the metrics above—not
                advice.
              </p>
              {report.ai_error && (
                <p
                  className="mt-3 rounded-lg border border-amber-500/35 bg-amber-950/30 px-3 py-2 text-sm text-amber-100"
                  role="status"
                >
                  {report.ai_error}
                </p>
              )}
              {report.ai_summary && (
                <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
                  {report.ai_summary}
                </div>
              )}
              {report.ai_summary && report.ai_model && (
                <p className="mt-3 text-xs text-slate-500">Model: {report.ai_model}</p>
              )}
            </section>
          )}

          <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-5">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Verdict
            </h3>
            <p className="mt-2 text-lg font-medium text-white">{report.verdict}</p>
          </section>

          <p className="text-xs leading-relaxed text-slate-500">{report.disclaimer}</p>
        </div>
      )}

      {loading && !report && (
        <p className="text-center text-sm text-slate-500">Loading fundamental data…</p>
      )}
    </div>
  );
}
