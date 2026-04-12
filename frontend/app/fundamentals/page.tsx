import { FundamentalReport } from "@/components/fundamental/FundamentalReport";

export default function FundamentalsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <h1 className="text-2xl font-semibold tracking-tight text-white">Fundamental analysis</h1>
        <p className="mt-1 text-sm text-slate-400">
          Rule-based snapshot from your FastAPI service (yfinance). For research only—not
          financial advice.
        </p>
        <div className="mt-8">
          <FundamentalReport />
        </div>
      </div>
    </div>
  );
}
