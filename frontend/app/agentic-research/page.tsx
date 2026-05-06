"use client";

import { useState } from "react";

import { postAgenticResearch, type AgenticResearchResponse } from "@/lib/agentic-research-api";

export default function AgenticResearchPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [secondary, setSecondary] = useState("");
  const [question, setQuestion] = useState(
    "Summarize fundamentals and recent news themes with citations. No buy/sell instructions.",
  );
  const [sessionId, setSessionId] = useState("demo-session");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AgenticResearchResponse | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const data = await postAgenticResearch({
        ticker,
        question,
        session_id: sessionId,
        secondary_ticker: secondary.trim() || undefined,
        include_buy_sell: true,
        include_news: true,
        include_fundamental: true,
        preferred_model: "gemini",
        max_steps: 3,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-semibold text-gray-900">Agentic research</h1>
      <p className="mt-2 text-sm text-gray-600">
        Planner → tools (fundamentals, news, optional buy/sell pipeline, history) → writer → rule critic.
        Session id ties into long-horizon memory (frequent tickers, topics, risk style).
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-sm font-medium text-gray-700">
            Primary ticker
            <input
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              maxLength={16}
            />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Secondary ticker (optional)
            <input
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
              value={secondary}
              onChange={(e) => setSecondary(e.target.value.toUpperCase())}
              maxLength={16}
              placeholder="e.g. MSFT for compare"
            />
          </label>
        </div>
        <label className="block text-sm font-medium text-gray-700">
          Session id
          <input
            className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            maxLength={64}
          />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Question
          <textarea
            className="mt-1 min-h-[100px] w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
          />
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-60"
        >
          {loading ? "Running…" : "Run agentic research"}
        </button>
      </form>

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      )}

      {result && (
        <div className="mt-8 space-y-6">
          <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-medium text-gray-900">Answer</h2>
            <p className="mt-3 whitespace-pre-wrap text-sm text-gray-800">{result.answer}</p>
            <p className="mt-4 text-xs text-gray-500">
              Critic: {result.critic_passed ? "passed" : "failed"} · Repair:{" "}
              {result.repair_attempted ? "yes" : "no"} · Planner retry:{" "}
              {result.plan_retry_attempted ? "yes" : "no"} · {result.latency_ms.toFixed(0)} ms ·{" "}
              {result.model_used}
            </p>
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-medium text-gray-900">Memory profile (after run)</h2>
            <pre className="mt-3 overflow-x-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-800">
              {JSON.stringify(result.memory_profile, null, 2)}
            </pre>
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-medium text-gray-900">Plan</h2>
            <ul className="mt-3 list-inside list-decimal text-sm text-gray-800">
              {result.plan.steps.map((s, i) => (
                <li key={i}>
                  <code className="text-teal-800">{s.tool}</code> {JSON.stringify(s.args)}
                </li>
              ))}
            </ul>
          </section>

          {result.citations.length > 0 && (
            <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-medium text-gray-900">Citations</h2>
              <p className="text-xs text-gray-500">Indices used: {result.citations_used.join(", ") || "none"}</p>
              <ul className="mt-3 space-y-2 text-sm">
                {result.citations.map((c, i) => (
                  <li key={i}>
                    <span className="font-medium text-gray-800">
                      [{i + 1}] {c.title}
                    </span>
                    {c.url ? (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-2 text-teal-700 underline hover:text-teal-900"
                      >
                        link
                      </a>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {(result.failed_checks.length > 0 || result.critic_notes.length > 0) && (
            <section className="rounded-xl border border-amber-200 bg-amber-50 p-6">
              <h2 className="text-lg font-medium text-amber-900">Critic detail</h2>
              <p className="mt-2 text-sm text-amber-900">Failed checks: {result.failed_checks.join(", ") || "—"}</p>
              <ul className="mt-2 list-inside list-disc text-sm text-amber-950">
                {result.critic_notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
