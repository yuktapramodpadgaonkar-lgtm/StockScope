"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { buildAssistantPayloadFromHistoryText } from "@/components/chat/chatUtils";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatMessage, type ChatMessageModel } from "@/components/chat/ChatMessage";
import { LoadingTypingIndicator } from "@/components/chat/LoadingTypingIndicator";
import { fetchThreadHistory, postChatQuery } from "@/lib/revati-api";
import type { ChatQueryResponse } from "@/lib/revati-types";

type ChatWindowProps = {
  initialThreadId?: string;
  onThreadIdChange?: (threadId: string) => void;
  seedPrompt?: string | null;
  onSeedPromptConsumed?: () => void;
};

export function ChatWindow({
  initialThreadId = "",
  onThreadIdChange,
  seedPrompt,
  onSeedPromptConsumed,
}: ChatWindowProps) {
  const [threadId, setThreadId] = useState(initialThreadId);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessageModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [hydrating, setHydrating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const prevInitialRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (seedPrompt == null || seedPrompt === "") return;
    setInput(seedPrompt);
    onSeedPromptConsumed?.();
  }, [seedPrompt, onSeedPromptConsumed]);

  useEffect(() => {
    const tid = (initialThreadId ?? "").trim();
    const prevRaw = prevInitialRef.current;
    prevInitialRef.current = initialThreadId;

    const prevTrim = (prevRaw ?? "").trim();

    setThreadId(tid);
    setError(null);
    if (!tid) {
      setMessages([]);
      return;
    }

    if (prevTrim !== "" && prevTrim !== tid) {
      setMessages([]);
    }

    let cancelled = false;
    setHydrating(true);
    (async () => {
      try {
        const th = await fetchThreadHistory(tid);
        if (cancelled) return;
        const next: ChatMessageModel[] = th.messages.map((m) => {
          if (m.role === "user") {
            return { role: "user", text: m.text, at: m.timestamp };
          }
          return {
            role: "assistant",
            at: m.timestamp,
            payload: buildAssistantPayloadFromHistoryText(m.text, th.thread_id, m.timestamp),
          };
        });
        setMessages(next);
      } catch {
        if (!cancelled) setMessages([]);
      } finally {
        if (!cancelled) setHydrating(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [initialThreadId]);

  useEffect(() => {
    const node = scrollerRef.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages, loading, error, hydrating]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;
    const userAt = new Date().toISOString();
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", text, at: userAt }]);
    setLoading(true);
    try {
      const res: ChatQueryResponse = await postChatQuery(text, threadId.trim() || null);
      setThreadId(res.thread_id);
      onThreadIdChange?.(res.thread_id);
      setMessages((m) => [...m, { role: "assistant", payload: res, at: res.timestamp }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [input, loading, onThreadIdChange, threadId]);

  const showEmpty = messages.length === 0 && !loading && !hydrating;

  return (
    <div className="flex min-h-[min(70vh,640px)] flex-1 flex-col overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-md">
      <div
        ref={scrollerRef}
        className="min-h-0 flex-1 space-y-4 overflow-y-auto bg-slate-50/80 px-4 py-5 sm:px-6"
      >
        {hydrating && messages.length === 0 ? (
          <p className="text-center text-sm text-slate-500">Loading conversation…</p>
        ) : null}

        {showEmpty ? (
          <div className="mx-auto max-w-md rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-10 text-center shadow-sm">
            <p className="text-sm font-semibold text-slate-800">Start a conversation</p>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              Ask about price drivers, sentiment, fundamentals, or comparisons. Answers include structured intent
              metadata and sources when available.
            </p>
          </div>
        ) : null}

        {messages.map((msg, i) => (
          <ChatMessage key={`${msg.role}-${i}-${msg.at}`} message={msg} />
        ))}

        {loading ? <LoadingTypingIndicator /> : null}

        {error ? (
          <div
            className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900 shadow-sm"
            role="alert"
          >
            <p className="font-semibold">Something went wrong</p>
            <p className="mt-1 text-rose-800/90">{error}</p>
          </div>
        ) : null}
      </div>

      <ChatInput value={input} onChange={setInput} onSend={() => void send()} loading={loading} />
    </div>
  );
}
