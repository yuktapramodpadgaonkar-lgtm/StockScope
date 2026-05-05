export type FundamentalMetrics = {
  market_cap: number | null;
  trailing_pe: number | null;
  forward_pe: number | null;
  profit_margin_pct: number | null;
  operating_margin_pct: number | null;
  roe_pct: number | null;
  debt_to_equity: number | null;
  current_ratio: number | null;
  revenue_growth_yoy_pct: number | null;
  earnings_growth_yoy_pct: number | null;
  dividend_yield_pct: number | null;
};

import { getAccessToken } from "@/lib/auth";
import { getApiBase } from "@/lib/auth-api";

export type FundamentalAnalysisResponse = {
  ticker: string;
  company_name: string;
  sector: string;
  industry: string;
  current_price: number | null;
  metrics: FundamentalMetrics;
  strengths: string[];
  risks: string[];
  verdict: string;
  disclaimer: string;
  ai_summary: string | null;
  ai_model: string | null;
  ai_error: string | null;
};

export async function fetchFundamentalAnalysis(
  ticker: string,
  includeLlm = false,
  provider?: string,
  model?: string,
): Promise<FundamentalAnalysisResponse> {
  const url = new URL(`${getApiBase()}/api/analysis/fundamental`);
  url.searchParams.set("ticker", ticker.trim());
  if (includeLlm) {
    url.searchParams.set("include_llm", "true");
    if (provider) url.searchParams.set("provider", provider);
    if (model) url.searchParams.set("model", model);
  }

  const headers: HeadersInit = {};
  const token = getAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(url.toString(), { cache: "no-store", headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<FundamentalAnalysisResponse>;
}
