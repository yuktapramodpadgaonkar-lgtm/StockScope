import Link from "next/link";

const FEATURES = [
  { href: "/buy-sell",         label: "Buy / Sell Analysis" },
  { href: "/market-movers",    label: "Market Movers" },
  { href: "/fundamentals",     label: "Fundamental Analysis" },
  { href: "/news-sentiment",   label: "News Sentiment" },
  { href: "/agentic-research", label: "Agentic Research" },
  { href: "/evaluation",       label: "Model Comparison" },
  { href: "/chatbot",          label: "AI Chatbot" },
  { href: "/history",          label: "History" },
];

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
          AI-powered research platform with agentic pipelines, RAG retrieval, and
          multi-model comparison (Gemini · LLaMA · Mistral). Sign in to get started.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        {FEATURES.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className="rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-600/25 transition hover:bg-teal-700"
          >
            {label}
          </Link>
        ))}
        <a
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noreferrer"
          className="rounded-lg border border-teal-300 bg-white px-5 py-2.5 text-sm font-semibold text-teal-700 transition hover:bg-teal-50"
        >
          API Docs
        </a>
      </div>
    </main>
  );
}
