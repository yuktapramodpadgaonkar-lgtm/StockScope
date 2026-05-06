import type { HistoryFilterTab } from "@/components/history/historyUtils";

const TABS: { id: HistoryFilterTab; label: string }[] = [
  { id: "all", label: "All" },
  { id: "chat", label: "Chat" },
  { id: "sentiment", label: "Sentiment" },
  { id: "fundamental", label: "Fundamental" },
  { id: "buy_sell", label: "Buy/Sell" },
];

type HistoryFilterTabsProps = {
  value: HistoryFilterTab;
  onChange: (tab: HistoryFilterTab) => void;
};

export function HistoryFilterTabs({ value, onChange }: HistoryFilterTabsProps) {
  return (
    <div
      className="flex flex-wrap gap-2 rounded-2xl border border-slate-200/80 bg-white/90 p-1.5 shadow-sm"
      role="tablist"
      aria-label="Filter history"
    >
      {TABS.map((tab) => {
        const active = value === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(tab.id)}
            className={`rounded-xl px-3.5 py-2 text-sm font-medium transition focus-visible:outline focus-visible:ring-2 focus-visible:ring-teal-500/40 ${
              active
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
