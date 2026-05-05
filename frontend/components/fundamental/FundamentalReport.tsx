"use client";

import { useCallback, useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { MetricCard } from "@/components/ui/MetricCard";
import {
  fetchFundamentalAnalysis,
  type FundamentalAnalysisResponse,
} from "@/lib/fundamental-api";
import { SectionCard } from "@/components/fundamental/SectionCard";
import { VerdictBadge } from "@/components/fundamental/VerdictBadge";

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
  /** Initial symbol for the lookup input (loads on mount). */
  defaultTicker?: string;
};

export function FundamentalReport({ defaultTicker = "AAPL" }: FundamentalReportProps) {
  const [input, setInput] = useState(defaultTicker);
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
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFundamentalAnalysis(sym);
      setReport(data);
    } catch (e) {
      setReport(null);
      setError(e instanceof Error ? e.message : "Failed to load fundamental analysis");
    } finally {
      setLoading(false);
    }
  }, []);

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
              placeholder="e.g. AAPL"
              className="rounded-xl border border-slate-300 bg-white px-3 py-2.5 font-mono text-sm text-slate-900 outline-none transition focus:border-slate-400 focus:ring-2 focus:ring-slate-200"
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
      </Card>

      {error && (
        <Card className="border-rose-200 bg-rose-50">
          <p className="text-sm font-medium text-rose-800">Could not load report</p>
          <p className="mt-1 text-sm text-rose-700">{error}</p>
        </Card>
      )}

      {loading && (
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

      {report && !loading && hasSearched && (
        <div className="space-y-6">
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
