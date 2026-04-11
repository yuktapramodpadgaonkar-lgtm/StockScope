import Link from "next/link";

import { FundamentalReport } from "@/components/fundamental/FundamentalReport";

export default function FundamentalsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900">
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-4xl flex-col gap-4 px-4 py-6 sm:px-6 lg:px-8">
          <Link
            href="/"
            className="text-sm font-medium text-emerald-400/90 hover:text-emerald-300"
          >
            ← Home
          </Link>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-white">
              Fundamental analysis
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Rule-based snapshot from your FastAPI service (yfinance). For research
              only—not financial advice.
            </p>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <FundamentalReport />
      </div>
    </div>
  );
}
