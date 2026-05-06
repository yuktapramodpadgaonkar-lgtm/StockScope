import { Card } from "@/components/ui/Card";

type MetricCardProps = {
  label: string;
  value: string;
  subtext?: string;
  tone?: "default" | "positive" | "negative";
};

export function MetricCard({ label, value, subtext, tone = "default" }: MetricCardProps) {
  const valueClass =
    tone === "positive"
      ? "text-emerald-600"
      : tone === "negative"
        ? "text-rose-600"
        : "text-slate-900";
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${valueClass}`}>{value}</p>
      {subtext ? <p className="mt-1 text-xs text-slate-500">{subtext}</p> : null}
    </Card>
  );
}
