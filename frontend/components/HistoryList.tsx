type HistoryRow = {
  id: string;
  title: string;
  subtitle?: string;
};

type HistoryListProps = {
  title: string;
  rows: HistoryRow[];
  loading?: boolean;
  emptyMessage?: string;
};

/**
 * Simple reusable list for history sections (Week 1).
 * TODO: Add keyboard nav / virtualization when lists grow.
 */
export function HistoryList({ title, rows, loading, emptyMessage }: HistoryListProps) {
  return (
    <section className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-emerald-400/90">{title}</h2>
      {loading ? (
        <p className="mt-3 text-sm text-slate-500">Loading…</p>
      ) : rows.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{emptyMessage ?? "Nothing here yet."}</p>
      ) : (
        <ul className="mt-3 divide-y divide-slate-800/80">
          {rows.map((row) => (
            <li key={row.id} className="py-3 first:pt-0 last:pb-0">
              <p className="text-sm font-medium text-slate-100">{row.title}</p>
              {row.subtitle ? <p className="mt-0.5 text-xs text-slate-500">{row.subtitle}</p> : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
