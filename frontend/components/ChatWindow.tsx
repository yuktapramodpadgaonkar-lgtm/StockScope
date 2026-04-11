"use client";

import { useCallback, useState } from "react";

import { postChatQuery } from "@/lib/revati-api";
import type { ChatQueryResponse } from "@/lib/revati-types";

type ChatMessage =
  | { role: "user"; text: string }
  | { role: "assistant"; payload: ChatQueryResponse };

type ChatWindowProps = {
  /** Seed thread id for requests; server echoes or generates. */
  initialThreadId?: string;
};

/**
 * Minimal chat UI wired to POST /api/chat/query (Week 1 stub).
 * TODO: Streaming tokens, tool traces, and persisted threads.
 */
export function ChatWindow({ initialThreadId = "thread_001" }: ChatWindowProps) {
  const [threadId, setThreadId] = useState(initialThreadId);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    try {
      const res = await postChatQuery(text, threadId);
      setThreadId(res.thread_id);
      setMessages((m) => [...m, { role: "assistant", payload: res }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [input, loading, threadId]);

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-xl border border-slate-800/80 bg-slate-900/40">
      <div className="min-h-[280px] flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && !loading && (
          <p className="text-sm text-slate-500">
            Ask about a stock move, sentiment, or a comparison. Week 1 uses keyword intent routing and
            mock citations.
          </p>
        )}
        {messages.map((msg, i) =>
          msg.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] rounded-lg bg-emerald-600/25 px-3 py-2 text-sm text-slate-100">
                {msg.text}
              </div>
            </div>
          ) : (
            <div key={i} className="space-y-2 rounded-lg border border-slate-800 bg-slate-950/60 p-3 text-sm">
              <p className="text-xs uppercase tracking-wide text-slate-500">
                Intent: <span className="text-emerald-400/90">{msg.payload.detected_intent}</span>
              </p>
              <p className="text-slate-100">{msg.payload.answer}</p>
              <ul className="list-inside list-disc text-xs text-slate-400">
                {msg.payload.summary_bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
              <div>
                <p className="text-xs font-medium text-slate-500">Citations</p>
                <ul className="mt-1 space-y-1">
                  {msg.payload.citations.map((c, idx) => (
                    <li key={`${c.url}-${idx}`} className="text-xs">
                      <a href={c.url} className="text-emerald-400 hover:underline" target="_blank" rel="noreferrer">
                        {c.title}
                      </a>
                      <span className="text-slate-500"> — {c.source}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <p className="text-[10px] text-slate-600">
                {msg.payload.timestamp} · {msg.payload.thread_id}
              </p>
              <p className="text-[10px] text-slate-500">{msg.payload.disclaimer}</p>
            </div>
          ),
        )}
        {loading && <p className="text-sm text-slate-500">Thinking…</p>}
        {error && <p className="text-sm text-rose-400">{error}</p>}
      </div>
      <div className="border-t border-slate-800/80 p-3">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), void send())}
            placeholder="Ask a question…"
            className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-emerald-500/50 focus:outline-none focus:ring-1 focus:ring-emerald-500/30"
            disabled={loading}
          />
          <button
            type="button"
            onClick={() => void send()}
            disabled={loading || !input.trim()}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
