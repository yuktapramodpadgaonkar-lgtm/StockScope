import type { NewsSentimentResponse } from "@/lib/revati-types";

type NewsSentimentReportProps = {
  data: NewsSentimentResponse;
};

function SentimentBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-400">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-800">
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
    <div className="space-y-6 rounded-xl border border-slate-800/80 bg-slate-900/50 p-5">
      <header className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Ticker</p>
          <h2 className="text-2xl font-semibold tracking-tight text-white">{data.ticker}</h2>
          {(data.date_from || data.date_to) && (
            <p className="mt-1 text-xs text-slate-500">
              {data.date_from ?? "…"} → {data.date_to ?? "…"}
            </p>
          )}
        </div>
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/40 px-3 py-2 text-center">
          <p className="text-[10px] uppercase tracking-wide text-slate-400">Overall</p>
          <p className="text-sm font-semibold capitalize text-emerald-300">{agg.overall_label}</p>
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <SentimentBar label="Positive" value={agg.positive} color="bg-emerald-500" />
        <SentimentBar label="Neutral" value={agg.neutral} color="bg-slate-400" />
        <SentimentBar label="Negative" value={agg.negative} color="bg-rose-500" />
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Major themes</h3>
        <ul className="mt-2 flex flex-wrap gap-2">
          {data.major_themes.map((t) => (
            <li
              key={t}
              className="rounded-full border border-slate-700 bg-slate-800/60 px-3 py-1 text-xs text-slate-200"
            >
              {t}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Articles</h3>
        <ul className="mt-2 space-y-3">
          {data.articles.map((a) => (
            <li
              key={a.url}
              className="rounded-lg border border-slate-800/90 bg-slate-950/50 p-3 text-sm"
            >
              <div className="flex flex-wrap items-center gap-2">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noreferrer"
                  className="font-medium text-emerald-300 hover:text-emerald-200"
                >
                  {a.headline}
                </a>
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                    a.sentiment === "positive"
                      ? "bg-emerald-500/20 text-emerald-300"
                      : a.sentiment === "negative"
                        ? "bg-rose-500/20 text-rose-300"
                        : "bg-slate-600/40 text-slate-300"
                  }`}
                >
                  {a.sentiment}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {a.source} · {a.published_at}
              </p>
              <p className="mt-2 text-xs text-slate-400">{a.summary}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Summary</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-300">{data.llm_summary}</p>
      </div>

      <p className="text-xs text-slate-500">{data.disclaimer}</p>
    </div>
  );
}
