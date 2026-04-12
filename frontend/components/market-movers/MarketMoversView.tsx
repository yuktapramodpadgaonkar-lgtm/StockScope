"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchMarketMovers,
  type MarketMoverItem,
  type MoverType,
  type TimeMode,
  type Universe,
} from "@/lib/market-movers-api";

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

const MOVER_TABS: { value: MoverType; label: string }[] = [
  { value: "gainers", label: "Top gainers" },
  { value: "losers", label: "Top losers" },
  { value: "52w_high", label: "52-week high" },
  { value: "52w_low", label: "52-week low" },
];

const LIMITS = [10, 25, 50, 100] as const;

type SortKey =
  | "symbol"
  | "company_name"
  | "price"
  | "change_percent"
  | "volume"
  | "market_cap"
  | "sector";

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

function formatCap(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  if (n >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
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
  const [moverType, setMoverType] = useState<MoverType>("gainers");
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
        type: moverType,
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
    if (!userSort) return items;
    return sortItems(items, userSort.key, userSort.dir);
  }, [items, userSort]);

  function toggleSort(key: SortKey) {
    setUserSort((prev) => {
      if (prev?.key === key) {
        return { key, dir: prev.dir === "asc" ? "desc" : "asc" };
      }
      return {
        key,
        dir:
          key === "symbol" || key === "company_name" || key === "sector" ? "asc" : "desc",
      };
    });
  }

  function sortIndicator(key: SortKey) {
    if (userSort?.key !== key) return "";
    return userSort.dir === "asc" ? " ↑" : " ↓";
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-white">Market movers</h1>
            <p className="mt-1 text-sm text-slate-400">
              Rankings from your FastAPI backend (cached server-side later). Data is for
              research only—not financial advice. Table order follows the server for each
              category until you sort by a column.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void load()}
            disabled={loading}
            className="self-start rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 shadow-md shadow-emerald-500/15 transition hover:bg-emerald-400 disabled:opacity-60"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4 shadow-xl backdrop-blur sm:flex-row sm:flex-wrap sm:items-end">
          <div className="flex flex-1 flex-col gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Category
            </span>
            <div className="flex flex-wrap gap-2">
              {MOVER_TABS.map((tab) => (
                <button
                  key={tab.value}
                  type="button"
                  onClick={() => setMoverType(tab.value)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    moverType === tab.value
                      ? "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40"
                      : "bg-slate-800/80 text-slate-300 hover:bg-slate-800"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <label className="flex min-w-[160px] flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Universe
            </span>
            <select
              value={universe}
              onChange={(e) => setUniverse(e.target.value as Universe)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none ring-emerald-500/0 transition focus:ring-2 focus:ring-emerald-500/40"
            >
              {UNIVERSES.map((u) => (
                <option key={u.value} value={u.value}>
                  {u.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex min-w-[140px] flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Time mode
            </span>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as TimeMode)}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:ring-2 focus:ring-emerald-500/40"
            >
              {MODES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex min-w-[100px] flex-col gap-1.5">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Rows
            </span>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:ring-2 focus:ring-emerald-500/40"
            >
              {LIMITS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && (
          <div
            className="rounded-lg border border-rose-500/40 bg-rose-950/40 px-4 py-3 text-sm text-rose-200"
            role="alert"
          >
            <p className="font-medium">Could not load market movers</p>
            <p className="mt-1 text-rose-200/80">{error}</p>
            <p className="mt-2 text-xs text-rose-200/60">
              Ensure the API is running:{" "}
              <code className="rounded bg-slate-950 px-1 py-0.5 text-rose-100">
                uvicorn app.main:app --reload --app-dir backend
              </code>{" "}
              from the repo root, and that{" "}
              <code className="rounded bg-slate-950 px-1 py-0.5">CORS_ORIGINS</code>{" "}
              includes this site&apos;s origin.
            </p>
          </div>
        )}

        <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/30 shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[880px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/80 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-3">
                    <button
                      type="button"
                      className="font-semibold hover:text-emerald-400"
                      onClick={() => toggleSort("symbol")}
                    >
                      Symbol{sortIndicator("symbol")}
                    </button>
                  </th>
                  <th className="px-4 py-3">
                    <button
                      type="button"
                      className="font-semibold hover:text-emerald-400"
                      onClick={() => toggleSort("company_name")}
                    >
                      Company{sortIndicator("company_name")}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-right">
                    <button
                      type="button"
                      className="font-semibold hover:text-emerald-400"
                      onClick={() => toggleSort("price")}
                    >
                      Price{sortIndicator("price")}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-right">
                    <button
                      type="button"
                      className="font-semibold hover:text-emerald-400"
                      onClick={() => toggleSort("change_percent")}
                    >
                      Chg %{sortIndicator("change_percent")}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-right">
                    <button
                      type="button"
                      className="font-semibold hover:text-emerald-400"
                      onClick={() => toggleSort("volume")}
                    >
                      Volume{sortIndicator("volume")}
                    </button>
                  </th>
                  <th className="px-4 py-3 text-right">
                    <button
                      type="button"
                      className="font-semibold hover:text-emerald-400"
                      onClick={() => toggleSort("market_cap")}
                    >
                      Mkt cap{sortIndicator("market_cap")}
                    </button>
                  </th>
                  <th className="px-4 py-3">
                    <button
                      type="button"
                      className="font-semibold hover:text-emerald-400"
                      onClick={() => toggleSort("sector")}
                    >
                      Sector{sortIndicator("sector")}
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading && displayRows.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                      Loading…
                    </td>
                  </tr>
                ) : displayRows.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                      No rows returned. Try another universe or refresh.
                    </td>
                  </tr>
                ) : (
                  displayRows.map((row) => (
                    <tr
                      key={row.symbol}
                      className="cursor-pointer border-b border-slate-800/80 transition hover:bg-slate-800/40"
                      onClick={() => setSelected(row)}
                    >
                      <td className="px-4 py-3 font-mono font-semibold text-emerald-400">
                        {row.symbol}
                      </td>
                      <td className="max-w-[200px] truncate px-4 py-3 text-slate-200">
                        {row.company_name ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-100">
                        {formatPrice(row.price)}
                      </td>
                      <td
                        className={`px-4 py-3 text-right tabular-nums ${
                          row.change_percent == null
                            ? "text-slate-500"
                            : row.change_percent > 0
                              ? "text-emerald-400"
                              : row.change_percent < 0
                                ? "text-rose-400"
                                : "text-slate-300"
                        }`}
                      >
                        {formatPct(row.change_percent)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-400">
                        {formatInt(row.volume)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-400">
                        {formatCap(row.market_cap)}
                      </td>
                      <td className="max-w-[140px] truncate px-4 py-3 text-slate-400">
                        {row.sector ?? "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <p className="text-center text-xs text-slate-600">
          Click a row for details. &quot;Run research&quot; will hook into buy/sell or chat
          when those routes exist.
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
          <div
            className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="mover-modal-title" className="text-lg font-semibold text-white">
              {selected.symbol}
              {selected.company_name ? (
                <span className="ml-2 font-normal text-slate-400">
                  {selected.company_name}
                </span>
              ) : null}
            </h2>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-slate-500">Price</dt>
                <dd className="font-mono text-slate-100">{formatPrice(selected.price)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Change %</dt>
                <dd className="font-mono text-slate-100">
                  {formatPct(selected.change_percent)}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">52W high</dt>
                <dd className="font-mono text-slate-100">{formatPrice(selected.high_52w)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">52W low</dt>
                <dd className="font-mono text-slate-100">{formatPrice(selected.low_52w)}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-slate-500">Industry</dt>
                <dd className="text-slate-200">{selected.industry ?? "—"}</dd>
              </div>
            </dl>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-emerald-400"
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
                className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
                onClick={() => setSelected(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
