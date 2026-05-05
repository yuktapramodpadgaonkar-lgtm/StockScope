import { FundamentalReport } from "@/components/fundamental/FundamentalReport";

export default function FundamentalsPage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Fundamental Analysis</h1>
        <p className="mt-1 text-sm text-slate-600">
          Evaluate company financial health using valuation, profitability, leverage, and growth metrics.
        </p>
        <div className="mt-6">
          <FundamentalReport />
        </div>
      </div>
    </div>
  );
}
