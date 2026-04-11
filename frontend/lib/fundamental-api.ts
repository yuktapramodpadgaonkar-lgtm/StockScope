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
};

function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  return base.replace(/\/$/, "");
}

export async function fetchFundamentalAnalysis(ticker: string): Promise<FundamentalAnalysisResponse> {
  const url = new URL(`${getApiBase()}/api/analysis/fundamental`);
  url.searchParams.set("ticker", ticker.trim());

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<FundamentalAnalysisResponse>;
}
