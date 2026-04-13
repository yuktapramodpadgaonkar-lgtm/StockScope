/** Mirrors backend BuySellReport (schema v1). */

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
