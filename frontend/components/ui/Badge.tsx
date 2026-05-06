type BadgeVariant = "buy" | "sell" | "neutral" | "positive" | "negative" | "default";

type BadgeProps = {
  label: string;
  variant?: BadgeVariant;
  className?: string;
};

const VARIANT_CLASS: Record<BadgeVariant, string> = {
  buy: "bg-emerald-50 text-emerald-700 border-emerald-200",
  sell: "bg-rose-50 text-rose-700 border-rose-200",
  neutral: "bg-amber-50 text-amber-700 border-amber-200",
  positive: "bg-emerald-50 text-emerald-700 border-emerald-200",
  negative: "bg-rose-50 text-rose-700 border-rose-200",
  default: "bg-slate-100 text-slate-700 border-slate-200",
};

export function Badge({ label, variant = "default", className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${VARIANT_CLASS[variant]} ${className}`}
    >
      {label}
    </span>
  );
}
