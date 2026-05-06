const DEFAULT_PROMPTS = [
  "Why is NVDA up today?",
  "Summarize AAPL news sentiment",
  "Analyze TSLA recent movement",
  "Explain MSFT fundamentals",
];

type SuggestedPromptsProps = {
  onSelect: (text: string) => void;
  disabled?: boolean;
  prompts?: string[];
};

export function SuggestedPrompts({
  onSelect,
  disabled,
  prompts = DEFAULT_PROMPTS,
}: SuggestedPromptsProps) {
  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Suggested prompts</p>
      <ul className="space-y-1.5">
        {prompts.map((text) => (
          <li key={text}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSelect(text)}
              className="w-full rounded-xl border border-slate-200/90 bg-white px-3 py-2.5 text-left text-xs font-medium leading-snug text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 hover:shadow disabled:opacity-40"
            >
              {text}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
