import type { NewsSentimentResponse } from "@/lib/revati-types";

type NewsSentimentReportProps = {
  data: NewsSentimentResponse;
};

function SentimentBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-teal-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

/**
 * Presents a news-sentiment API payload (mock or live).
 * TODO: Swap static bars for charts when analytics layer lands.
 */
export function NewsSentimentReport({ data }: NewsSentimentReportProps) {
  const { aggregate_sentiment: agg } = data;

  return (
    <div className="space-y-6 rounded-xl border border-gray-200/80 bg-teal-50/50 p-5">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Ticker</p>
          <h2 className="text-2xl font-semibold tracking-tight text-gray-900">{data.ticker}</h2>
          {(data.date_from || data.date_to) && (
            <p className="mt-1 text-xs text-gray-400">
              {data.date_from ?? "…"} → {data.date_to ?? "…"}
            </p>
          )}
        </div>
        <div className="rounded-lg border border-teal-500/30 bg-teal-950/40 px-3 py-2 text-center">
          <p className="text-[10px] uppercase tracking-wide text-gray-500">Overall</p>
          <p className="text-sm font-semibold capitalize text-teal-300">{agg.overall_label}</p>
        </div>
      </header>
      {data.fallback_used ? (
        <p className="rounded border border-amber-600/40 bg-amber-900/20 px-3 py-2 text-xs text-amber-300">
          Fallback mode used: live Finnhub feed unavailable, so sample articles were used.
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <SentimentBar label="Positive" value={agg.positive} color="bg-teal-500" />
        <SentimentBar label="Neutral" value={agg.neutral} color="bg-gray-400" />
        <SentimentBar label="Negative" value={agg.negative} color="bg-rose-500" />
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Major themes</h3>
        <ul className="mt-2 flex flex-wrap gap-2">
          {data.major_themes.map((t) => (
            <li
              key={t}
              className="rounded-full border border-teal-200 bg-teal-100/60 px-3 py-1 text-xs text-gray-800"
            >
              {t}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Articles</h3>
        <ul className="mt-2 space-y-3">
          {data.articles.map((a) => (
            <li
              key={a.url}
              className="rounded-lg border border-gray-200/90 bg-white/50 p-3 text-sm"
            >
              <div className="flex flex-wrap items-center gap-2">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-teal-300 hover:text-teal-200"
                >
                  {a.headline}
                </a>
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                    a.sentiment === "positive"
                      ? "bg-teal-500/20 text-teal-300"
                      : a.sentiment === "negative"
                        ? "bg-rose-500/20 text-rose-300"
                        : "bg-gray-200/40 text-gray-700"
                  }`}
                >
                  {a.sentiment}
                </span>
              </div>
              <p className="mt-1 text-xs text-gray-400">
                {a.source} · {a.published_at}
              </p>
              <p className="mt-2 text-xs text-gray-500">{a.summary}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white/60 p-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Summary</h3>
        <p className="mt-2 text-sm leading-relaxed text-gray-700">{data.summary}</p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white/60 p-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Citations</h3>
        <ul className="mt-2 space-y-1">
          {data.citations.map((c) => (
            <li key={`${c.url}-${c.published_at}`} className="text-xs text-gray-500">
              <a href={c.url} target="_blank" rel="noreferrer" className="text-teal-400 hover:underline">
                {c.title}
              </a>{" "}
              — {c.source} ({c.published_at})
            </li>
          ))}
        </ul>
      </div>

      <p className="text-xs text-gray-400">{data.disclaimer}</p>
    </div>
  );
}
