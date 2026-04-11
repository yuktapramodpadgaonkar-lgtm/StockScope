export type Universe = "all" | "sp500" | "dow30" | "nasdaq100" | "russell1000";
export type TimeMode = "intraday" | "previous_day";
export type MoverType = "gainers" | "losers" | "52w_high" | "52w_low";

export type MarketMoverItem = {
  symbol: string;
  company_name: string | null;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  volume: number | null;
  market_cap: number | null;
  sector: string | null;
  industry: string | null;
  high_52w: number | null;
  low_52w: number | null;
};

export type MarketMoversResponse = {
  universe: Universe;
  mode: TimeMode;
  type: MoverType;
  count: number;
  items: MarketMoverItem[];
};

function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  return base.replace(/\/$/, "");
}

export async function fetchMarketMovers(params: {
  universe: Universe;
  mode: TimeMode;
  type: MoverType;
  limit: number;
}): Promise<MarketMoversResponse> {
  const url = new URL(`${getApiBase()}/api/market-movers`);
  url.searchParams.set("universe", params.universe);
  url.searchParams.set("mode", params.mode);
  url.searchParams.set("type", params.type);
  url.searchParams.set("limit", String(params.limit));

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<MarketMoversResponse>;
}
