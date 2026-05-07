import { getAccessToken } from "@/lib/auth";
import { getApiBase } from "@/lib/auth-api";

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

export type RagEvidenceItem = {
  chunk_id?: string | null;
  title?: string | null;
  url?: string | null;
  section_key?: string | null;
  text_preview: string;
  retrieval_score?: number | null;
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
  ai_summary: string | null;
  ai_model: string | null;
  ai_error: string | null;
  rag_evidence?: RagEvidenceItem[] | null;
  rag_error?: string | null;
};

export type FundamentalFetchOptions = {
  includeLlm?: boolean;
  /** Ingest SEC filing chunks and return `rag_evidence` (optional narrative context). */
  includeRag?: boolean;
  /** Matches backend `preferred_model`: gemini | llama | mistral */
  preferredModel?: string;
};

export async function fetchFundamentalAnalysis(
  ticker: string,
  options: FundamentalFetchOptions = {},
): Promise<FundamentalAnalysisResponse> {
  const { includeLlm = false, includeRag = false, preferredModel } = options;

  const url = new URL(`${getApiBase()}/api/analysis/fundamental`);
  url.searchParams.set("ticker", ticker.trim());
  if (includeLlm) {
    url.searchParams.set("include_llm", "true");
    if (preferredModel) url.searchParams.set("preferred_model", preferredModel);
  }
  if (includeRag) {
    url.searchParams.set("include_rag", "true");
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
