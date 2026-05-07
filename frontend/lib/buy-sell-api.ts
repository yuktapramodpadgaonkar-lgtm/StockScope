/** Mirrors backend BuySellReport (schema v1.x; optional `agent_pipeline`, `memory`). */

import { getAccessToken } from "@/lib/auth";

export type Recommendation = "BUY" | "HOLD" | "SELL";

export type CitationItem = {
  id: string;
  title: string;
  source: string;
  url: string | null;
  date: string | null;
  snippet: string | null;
};

export type ValuationAnalysis = {
  pe: number | null;
  dcf_value: number | null;
  current_price: number | null;
  implied_upside: number | null;
};

export type CriticResult = {
  passed: boolean;
  incomplete_evidence: boolean;
  flags: string[];
  notes: string[];
};

export type MemoryBlock = {
  session_id: string;
  recent_tickers: string[];
  preferred_horizon: string | null;
  analysis_style: string | null;
  session_summary: string;
  follow_up_context: string;
};

export type AgentPipelineBlock = {
  planner_version: string;
  plan_summary: string;
  planned_steps: { id: string; description: string }[];
  execution_trace: {
    step_id: string;
    description: string;
    status: string;
    duration_ms: number;
    detail: string | null;
  }[];
  critic: CriticResult;
};

export type BuySellReport = {
  schema_version: string;
  ticker: string;
  recommendation: Recommendation;
  confidence: number;
  optimal_timeframe: string;
  setup_quality: number;
  disclaimer: string;
  investment_thesis: {
    summary: string;
    key_drivers: string[];
  };
  fundamental_analysis: {
    score: number;
    weight: number;
    business_performance: string;
    valuation_analysis: ValuationAnalysis;
    bull_bear_integration: string;
    verdict: string;
  };
  technical_analysis: {
    score: number;
    weight: number;
    trend_analysis: string;
    indicators: {
      rsi: number | null;
      macd_signal: string;
      ma_50: number | null;
      ma_200: number | null;
      price_vs_ma: string;
    };
    verdict: string;
  };
  sentiment_analysis: {
    score: number;
    weight: number;
    recent_developments: string[];
    verdict: string;
  };
  final_verdict: {
    overall_score: number;
    rating: string;
    why_dimensions_align: string;
    conflicts: string;
  };
  risk_assessment: {
    key_risks: string[];
    action_plan: {
      if_you_own: string;
      if_you_want_to_buy: string;
    };
  };
  citations: CitationItem[];
  /** Phase 6 — present on `/api/buy-sell/analyze` when `use_agent_pipeline=true` (default). */
  agent_pipeline?: AgentPipelineBlock | null;
  /** Phase 7 — present when `use_memory=true` (default) and memory is enabled on the server. */
  memory?: MemoryBlock | null;
};

function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  return base.replace(/\/$/, "");
}

export async function fetchMockBuySellReport(): Promise<BuySellReport> {
  const res = await fetch(`${getApiBase()}/api/buy-sell/report/mock`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<BuySellReport>;
}

/** Call the real agentic scoring pipeline for any ticker. */
export async function fetchBuySellReport(ticker: string): Promise<BuySellReport> {
  const sym = ticker.trim().toUpperCase();
  const url =
    `${getApiBase()}/api/buy-sell/analyze/${encodeURIComponent(sym)}` +
    `?include_llm_review=true&use_agent_pipeline=true`;
  const token = getAccessToken();
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(url, { cache: "no-store", headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<BuySellReport>;
}
