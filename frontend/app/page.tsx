import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 px-6 py-16">
      <div>
        <p className="text-sm font-medium uppercase tracking-widest text-emerald-400/90">
          StockScope AI
        </p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">
          CMPE-258 research platform
        </h1>
        <p className="mt-4 text-lg text-slate-400">
          Browse market movers backed by the FastAPI service. More modules (buy/sell,
          chat) plug in here as your team ships them.
        </p>
      </div>
      <div className="flex flex-wrap gap-4">
        <Link
          href="/market-movers"
          className="rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-400"
        >
          Open Market Movers
        </Link>
        <a
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-slate-700 bg-slate-900/80 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:border-slate-500"
        >
          API docs (Swagger)
        </a>
      </div>
    </main>
  );
}
