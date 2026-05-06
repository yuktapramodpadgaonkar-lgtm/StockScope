type VerdictBadgeProps = {
  verdict: string;
};

function classifyVerdict(verdict: string): "strong" | "moderate" | "weak" | "risky" {
  const v = verdict.toLowerCase();
  if (v.includes("strong")) return "strong";
  if (v.includes("risk")) return "risky";
  if (v.includes("weak")) return "weak";
  return "moderate";
}

export function VerdictBadge({ verdict }: VerdictBadgeProps) {
  const normalized = classifyVerdict(verdict);
  const styleMap = {
    strong: "border-emerald-200 bg-emerald-50 text-emerald-700",
    moderate: "border-sky-200 bg-sky-50 text-sky-700",
    weak: "border-amber-200 bg-amber-50 text-amber-700",
    risky: "border-rose-200 bg-rose-50 text-rose-700",
  } as const;
  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${styleMap[normalized]}`}
    >
      {normalized}
    </span>
  );
}
