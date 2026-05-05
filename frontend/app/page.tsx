import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 px-6 py-16">
      <div>
        <p className="text-sm font-medium uppercase tracking-widest text-teal-800">
          StockScope AI
        </p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-gray-900">
          Stock Research Platform
        </h1>
        <p className="mt-4 text-lg text-gray-500">
          Explore market movers, fundamentals, and history—use the chat button to open the AI assistant. Wired to a shared FastAPI
          backend. Use the links below to try each module; buy/sell and deeper AI features
          will layer in as the course project grows.
        </p>
      </div>
      <div className="flex flex-wrap gap-4">
        <Link
          href="/buy-sell"
          className="rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition hover:bg-teal-700"
        >
          Buy / Sell report
        </Link>
        <Link
          href="/market-movers"
          className="rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition hover:bg-teal-700"
        >
          Market Movers
        </Link>
        <Link
          href="/fundamentals"
          className="rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition hover:bg-teal-700"
        >
          Fundamental Analysis
        </Link>
        <Link
          href="/history"
          className="rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition hover:bg-teal-700"
        >
          History
        </Link>
        <a
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition hover:bg-teal-700"
        >
          API Docs
        </a>
      </div>
    </main>
  );
}
