"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchMarketMovers,
  type MarketMoverItem,
  type TimeMode,
  type Universe,
} from "@/lib/market-movers-api";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { MetricCard } from "@/components/ui/MetricCard";
import { SectionHeader } from "@/components/ui/SectionHeader";

const UNIVERSES: { value: Universe; label: string }[] = [
  { value: "all", label: "All (sample)" },
  { value: "sp500", label: "S&P 500" },
  { value: "dow30", label: "Dow Jones" },
  { value: "nasdaq100", label: "Nasdaq 100" },
  { value: "russell1000", label: "Russell 1000" },
];

const MODES: { value: TimeMode; label: string }[] = [
  { value: "intraday", label: "Intraday" },
  { value: "previous_day", label: "Previous day" },
];

type UiMoverTab = "gainers" | "losers" | "most_active";

const MOVER_TABS: { value: UiMoverTab; label: string }[] = [
  { value: "gainers", label: "Gainers" },
  { value: "losers", label: "Losers" },
  { value: "most_active", label: "Most active" },
];

const LIMITS = [10, 25, 50, 100] as const;

type SortKey =
  | "symbol"
  | "price"
  | "change_percent"
  | "volume";

function formatPrice(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function formatInt(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toLocaleString();
}

function sortItems(
  items: MarketMoverItem[],
  key: SortKey,
  dir: "asc" | "desc",
): MarketMoverItem[] {
  const mult = dir === "asc" ? 1 : -1;
  return [...items].sort((a, b) => {
    const va = a[key];
    const vb = b[key];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === "string" && typeof vb === "string") {
      return mult * va.localeCompare(vb);
    }
    if (typeof va === "number" && typeof vb === "number") {
      return mult * (va - vb);
    }
    return 0;
  });
}

export function MarketMoversView() {
  const [universe, setUniverse] = useState<Universe>("sp500");
  const [mode, setMode] = useState<TimeMode>("intraday");
  const [moverType, setMoverType] = useState<UiMoverTab>("gainers");
  const [limit, setLimit] = useState<number>(25);

  const [items, setItems] = useState<MarketMoverItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /** null = keep rows in API rank order (required for losers / 52w views). */
  const [userSort, setUserSort] = useState<{ key: SortKey; dir: "asc" | "desc" } | null>(
    null,
  );

  const [selected, setSelected] = useState<MarketMoverItem | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMarketMovers({
        universe,
        mode,
        type: moverType === "most_active" ? "gainers" : moverType,
        limit,
      });
      setItems(data.items);
    } catch (e) {
      setItems([]);
      setError(e instanceof Error ? e.message : "Failed to load movers");
    } finally {
      setLoading(false);
    }
  }, [universe, mode, moverType, limit]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setUserSort(null);
  }, [universe, mode, moverType, limit]);

  useEffect(() => {
    if (!selected) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelected(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selected]);

  const displayRows = useMemo(() => {
    const baseRows =
      moverType === "most_active"
        ? [...items].sort((a, b) => (b.volume ?? 0) - (a.volume ?? 0))
        : items;
    if (!userSort) return baseRows;
    return sortItems(baseRows, userSort.key, userSort.dir);
  }, [items, moverType, userSort]);

  const stats = useMemo(() => {
    const positive = displayRows.filter((x) => (x.change_percent ?? 0) > 0).length;
    const negative = displayRows.filter((x) => (x.change_percent ?? 0) < 0).length;
    const avgMove =
      displayRows.length > 0
        ? displayRows.reduce((acc, x) => acc + (x.change_percent ?? 0), 0) / displayRows.length
        : 0;
    return {
      positive,
      negative,
      avgMove,
      totalVolume: displayRows.reduce((acc, x) => acc + (x.volume ?? 0), 0),
    };
  }, [displayRows]);

  function toggleSort(key: SortKey) {
    setUserSort((prev) => {
      if (prev?.key === key) {
        return { key, dir: prev.dir === "asc" ? "desc" : "asc" };
      }
      return {
        key,
        dir: key === "symbol" ? "asc" : "desc",
      };
    });
  }

  function sortAriaSort(key: SortKey): "ascending" | "descending" | "none" {
    if (userSort?.key !== key) return "none";
    return userSort.dir === "asc" ? "ascending" : "descending";
  }

  function SortHeader({
    label,
    sortKey,
    align = "left",
  }: {
    label: string;
    sortKey: SortKey;
    align?: "left" | "right";
  }) {
    const active = userSort?.key === sortKey;
    return (
      <th
        scope="col"
        className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50/95 px-5 py-3.5 backdrop-blur-sm"
        aria-sort={sortAriaSort(sortKey)}
      >
        <div className={align === "right" ? "flex justify-end" : "flex justify-start"}>
          <button
            type="button"
            onClick={() => toggleSort(sortKey)}
            className={`group inline-flex items-center gap-1.5 rounded-lg px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500 transition focus-visible:outline focus-visible:ring-2 focus-visible:ring-slate-400/60 ${
              active
                ? "text-slate-900"
                : "hover:bg-slate-100/80 hover:text-slate-800"
            }`}
          >
            <span>{label}</span>
            <span
              className={`flex flex-col leading-[0.55] text-[9px] tabular-nums ${
                active ? "text-slate-700" : "text-slate-400 group-hover:text-slate-600"
              }`}
              aria-hidden
            >
              <span className={active && userSort?.dir === "asc" ? "text-slate-900" : ""}>▲</span>
              <span className={active && userSort?.dir === "desc" ? "text-slate-900" : ""}>▼</span>
            </span>
          </button>
        </div>
      </th>
    );
  }

  function changeCellClasses(pct: number | null | undefined): string {
    if (pct == null || Number.isNaN(pct)) {
      return "bg-slate-100/80 text-slate-500 ring-1 ring-slate-200/80";
    }
    if (pct > 0) {
      return "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/70";
    }
    if (pct < 0) {
      return "bg-rose-50 text-rose-700 ring-1 ring-rose-200/70";
    }
    return "bg-slate-100/80 text-slate-600 ring-1 ring-slate-200/80";
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        <Card>
          <SectionHeader
            title="Market Movers"
            description="Track gainers, losers and most active symbols from the FastAPI market-movers API."
            actions={
              <button
                type="button"
                onClick={() => void load()}
                disabled={loading}
                className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-60"
              >
                {loading ? "Refreshing..." : "Refresh"}
              </button>
            }
          />
          <div className="mt-6 flex flex-wrap gap-2">
            {MOVER_TABS.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => setMoverType(tab.value)}
                className={`rounded-xl border px-3 py-2 text-sm font-medium transition ${
                  moverType === tab.value
                    ? "border-slate-900 bg-slate-900 text-white shadow-sm"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Universe
              </span>
              <select
                value={universe}
                onChange={(e) => setUniverse(e.target.value as Universe)}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-slate-300"
              >
                {UNIVERSES.map((u) => (
                  <option key={u.value} value={u.value}>
                    {u.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Time mode
              </span>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as TimeMode)}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-slate-300"
              >
                {MODES.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Rows</span>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:ring-2 focus:ring-slate-300"
              >
                {LIMITS.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Rows" value={String(displayRows.length)} />
          <MetricCard label="Avg Move" value={formatPct(stats.avgMove)} tone={stats.avgMove >= 0 ? "positive" : "negative"} />
          <MetricCard label="Advancers" value={String(stats.positive)} tone="positive" />
          <MetricCard label="Decliners" value={String(stats.negative)} tone="negative" subtext={`Volume ${formatInt(stats.totalVolume)}`} />
        </div>

        {error ? (
          <Card className="border-rose-200 bg-rose-50">
            <p className="text-sm font-semibold text-rose-700">Could not load market movers</p>
            <p className="mt-1 text-sm text-rose-600">{error}</p>
          </Card>
        ) : null}

        <Card className="overflow-hidden p-0 shadow-md ring-1 ring-slate-200/80">
          <div className="max-h-[min(70vh,780px)] overflow-auto">
            <table className="w-full min-w-[720px] border-collapse text-left text-sm">
              <thead>
                <tr className="shadow-[inset_0_-1px_0_0_rgb(226_232_240)]">
                  <SortHeader label="Ticker" sortKey="symbol" />
                  <SortHeader label="Last" sortKey="price" align="right" />
                  <SortHeader label="% Chg" sortKey="change_percent" align="right" />
                  <SortHeader label="Volume" sortKey="volume" align="right" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {loading && displayRows.length === 0 ? (
                  [...Array(6)].map((_, idx) => (
                    <tr key={idx} className="border-0">
                      <td className="px-5 py-3.5"><LoadingSkeleton className="h-5 w-20" /></td>
                      <td className="px-5 py-3.5 text-right"><LoadingSkeleton className="ml-auto h-5 w-16" /></td>
                      <td className="px-5 py-3.5 text-right"><LoadingSkeleton className="ml-auto h-5 w-20" /></td>
                      <td className="px-5 py-3.5 text-right"><LoadingSkeleton className="ml-auto h-5 w-24" /></td>
                    </tr>
                  ))
                ) : displayRows.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-5 py-14 text-center text-sm text-slate-500">
                      No rows returned. Try another tab, universe, or refresh.
                    </td>
                  </tr>
                ) : (
                  displayRows.map((row) => (
                    <tr
                      key={row.symbol}
                      className="cursor-pointer border-0 transition-colors duration-150 hover:bg-slate-50/90 hover:shadow-[inset_3px_0_0_0_rgb(15_23_42)]"
                      onClick={() => setSelected(row)}
                    >
                      <td className="whitespace-nowrap px-5 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <span className="font-mono text-sm font-semibold tracking-tight text-slate-900">
                            {row.symbol}
                          </span>
                          <Badge
                            label={
                              row.change_percent == null
                                ? "Flat"
                                : row.change_percent >= 0
                                  ? "Up"
                                  : "Down"
                            }
                            variant={
                              row.change_percent == null
                                ? "neutral"
                                : row.change_percent >= 0
                                  ? "positive"
                                  : "negative"
                            }
                          />
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-right font-medium tabular-nums text-slate-900">
                        {formatPrice(row.price)}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <span
                          className={`inline-flex min-w-[5.25rem] justify-end rounded-lg px-2.5 py-1 text-sm font-semibold tabular-nums ${changeCellClasses(row.change_percent)}`}
                        >
                          {formatPct(row.change_percent)}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-right text-sm tabular-nums text-slate-600">
                        {formatInt(row.volume)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>

        <p className="text-center text-xs text-slate-500">
          Click any row to view more context and launch research.
        </p>
      </div>

      {selected && (
        <div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          aria-labelledby="mover-modal-title"
          onClick={() => setSelected(null)}
        >
          <div onClick={(e) => e.stopPropagation()}>
            <Card className="max-h-[90vh] w-full max-w-lg overflow-y-auto p-6">
              <h2 id="mover-modal-title" className="text-xl font-semibold text-slate-900">
                {selected.symbol}
                {selected.company_name ? (
                  <span className="ml-2 font-normal text-slate-500">
                    {selected.company_name}
                  </span>
                ) : null}
              </h2>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-slate-500">Price</dt>
                  <dd className="font-mono text-slate-900">{formatPrice(selected.price)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Change %</dt>
                  <dd className="font-mono text-slate-900">
                    {formatPct(selected.change_percent)}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">52W high</dt>
                  <dd className="font-mono text-slate-900">{formatPrice(selected.high_52w)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">52W low</dt>
                  <dd className="font-mono text-slate-900">{formatPrice(selected.low_52w)}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-slate-500">Industry</dt>
                  <dd className="text-slate-800">{selected.industry ?? "—"}</dd>
                </div>
              </dl>
              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                  onClick={() => {
                    alert(
                      `Run research for ${selected.symbol} — connect this to your Buy/Sell or Chat flow.`,
                    );
                  }}
                >
                  Run research
                </button>
                <button
                  type="button"
                  className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                  onClick={() => setSelected(null)}
                >
                  Close
                </button>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
