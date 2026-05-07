"use client";

import { useState } from "react";

import { NewsSentimentReport } from "@/components/NewsSentimentReport";
import { postNewsSentiment } from "@/lib/revati-api";
import type { NewsSentimentResponse } from "@/lib/revati-types";

export default function NewsSentimentPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [maxArticles, setMaxArticles] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<NewsSentimentResponse | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const sym = ticker.trim().toUpperCase();
    if (!sym) return;
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const data = await postNewsSentiment({ ticker: sym, max_articles: maxArticles, use_rag: true });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-semibold text-gray-900">News Sentiment</h1>
      <p className="mt-2 text-sm text-gray-600">
        FinBERT neural sentiment classification + LLM theme extraction, grounded by hybrid RAG retrieval.
      </p>

      <form
        onSubmit={onSubmit}
        className="mt-8 flex flex-wrap items-end gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm"
      >
        <label className="block text-sm font-medium text-gray-700">
          Ticker
          <input
            className="mt-1 w-32 rounded-lg border border-gray-300 px-3 py-2 font-mono text-gray-900 uppercase"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            maxLength={10}
            required
          />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Max articles
          <select
            className="mt-1 block rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
            value={maxArticles}
            onChange={(e) => setMaxArticles(Number(e.target.value))}
          >
            {[5, 10, 15, 20].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-teal-600 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-60"
        >
          {loading ? "Analysing…" : "Analyse"}
        </button>
      </form>

      {loading && (
        <div className="mt-6 flex items-center gap-3 rounded-xl border border-teal-200 bg-teal-50 px-5 py-4">
          <svg className="h-4 w-4 animate-spin text-teal-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <span className="text-sm font-medium text-teal-800">Fetching news and running FinBERT classification…</span>
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-8">
          <NewsSentimentReport data={result} />
        </div>
      )}
    </div>
  );
}
