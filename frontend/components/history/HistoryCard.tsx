"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import { fetchThreadHistory } from "@/lib/revati-api";
import type { ThreadMessage } from "@/lib/revati-types";

import type { UnifiedHistoryItem } from "@/components/history/historyUtils";
import {
  analysisTypeLabel,
  extractUrls,
  formatHistoryTimestamp,
  previewText,
  researchTabCategory,
} from "@/components/history/historyUtils";
import { Badge } from "@/components/ui/Badge";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";

type HistoryCardProps = {
  item: UnifiedHistoryItem;
};

function badgeVariant(item: UnifiedHistoryItem): "default" | "neutral" | "positive" {
  if (item.kind === "chat") return "default";
  if (item.kind === "prompt") return "neutral";
  const cat = researchTabCategory(item.data.type);
  if (cat === "sentiment") return "positive";
  if (cat === "fundamental") return "default";
  if (cat === "buy_sell") return "neutral";
  return "default";
}

function researchDeepLink(type: string): string | null {
  const cat = researchTabCategory(type);
  if (cat === "sentiment") return "/chatbot";
  if (cat === "fundamental") return "/fundamentals";
  if (cat === "buy_sell") return "/buy-sell";
  return null;
}

export function HistoryCard({ item }: HistoryCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [threadLoading, setThreadLoading] = useState(false);
  const [threadError, setThreadError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ThreadMessage[] | null>(null);

  const title = useMemo(() => {
    if (item.kind === "chat") return item.data.title || "Chat thread";
    if (item.kind === "research") return `${item.data.ticker} · ${item.data.type.replace(/_/g, " ")}`;
    return item.data.title;
  }, [item]);

  const ticker = item.kind === "research" ? item.data.ticker : null;

  const timestamp =
    item.kind === "chat"
      ? item.data.last_updated
      : item.kind === "research"
        ? item.data.created_at
        : null;

  const preview = useMemo(() => {
    if (item.kind === "prompt") return previewText(item.data.prompt_text);
    if (item.kind === "chat") return previewText(item.data.title);
    return `Analysis run for ${item.data.ticker}. Expand for details or open the workspace.`;
  }, [item]);

  const loadThread = useCallback(async () => {
    if (item.kind !== "chat") return;
    setThreadLoading(true);
    setThreadError(null);
    try {
      const res = await fetchThreadHistory(item.data.thread_id);
      setMessages(res.messages);
    } catch (e) {
      setThreadError(e instanceof Error ? e.message : "Could not load thread");
    } finally {
      setThreadLoading(false);
    }
  }, [item]);

  const expandedBody = useMemo(() => {
    if (item.kind === "prompt") {
      return item.data.prompt_text;
    }
    if (item.kind === "research") {
      const lines = [
        `Type: ${item.data.type}`,
        `Ticker: ${item.data.ticker}`,
        `Run at: ${formatHistoryTimestamp(item.data.created_at)}`,
      ];
      if (item.data.model_used) lines.push(`Model: ${item.data.model_used}`);
      if (item.data.provider) lines.push(`Provider: ${item.data.provider}`);
      return lines.join("\n");
    }
    if (item.kind === "chat") {
      if (threadLoading) return "";
      if (threadError) return threadError;
      if (!messages?.length) return "No messages in this thread yet.";
      return messages
        .map((m) => {
          let line = `[${m.role}] ${m.text}`;
          if (m.role === "assistant" && m.model_used) {
            const fallbackNote = m.fallback_used ? " (fallback)" : "";
            line += `\n  ↳ ${m.model_used}${fallbackNote}${m.provider ? ` · ${m.provider}` : ""}`;
          }
          return line;
        })
        .join("\n\n");
    }
    return "";
  }, [item, messages, threadError, threadLoading]);

  const urls = useMemo(() => {
    if (item.kind === "prompt") return extractUrls(item.data.prompt_text);
    if (item.kind === "chat" && messages) {
      return extractUrls(...messages.map((m) => m.text));
    }
    if (item.kind === "chat" && !expanded) return extractUrls(item.data.title);
    return [];
  }, [item, messages, expanded]);

  const typeLabel = analysisTypeLabel(item.kind, item.kind === "research" ? item.data.type : undefined);

  const researchWorkspaceHref = item.kind === "research" ? researchDeepLink(item.data.type) : null;

  return (
    <article className="group rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge label={typeLabel} variant={badgeVariant(item)} />
            {ticker ? (
              <span className="rounded-lg bg-slate-100 px-2 py-0.5 font-mono text-xs font-semibold text-slate-700">
                {ticker}
              </span>
            ) : null}
            {item.kind === "research" && item.data.model_used ? (
              <span className="inline-flex items-center rounded-full border border-teal-200 bg-teal-50 px-2 py-0.5 text-[10px] font-semibold text-teal-700">
                {item.data.model_used}
              </span>
            ) : null}
          </div>
          <h3 className="text-base font-semibold leading-snug text-slate-900">{title}</h3>
          {timestamp ? (
            <p className="text-xs font-medium text-slate-500">{formatHistoryTimestamp(timestamp)}</p>
          ) : (
            <p className="text-xs font-medium text-slate-500">Saved prompt</p>
          )}
          <p className="text-sm leading-relaxed text-slate-600">{preview}</p>
        </div>
        <button
          type="button"
          aria-expanded={expanded}
          onClick={() => {
            if (expanded) {
              setExpanded(false);
              return;
            }
            setExpanded(true);
            if (item.kind === "chat" && messages === null) {
              void loadThread();
            }
          }}
          className="shrink-0 self-start rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 focus-visible:outline focus-visible:ring-2 focus-visible:ring-teal-500/40"
        >
          {expanded ? "Collapse" : "Expand"}
        </button>
      </div>

      {expanded ? (
        <div className="mt-4 border-t border-slate-100 pt-4">
          {item.kind === "chat" && threadLoading ? (
            <div className="space-y-2" aria-busy="true">
              <LoadingSkeleton className="h-4 w-full" />
              <LoadingSkeleton className="h-4 w-5/6" />
              <LoadingSkeleton className="h-4 w-4/6" />
            </div>
          ) : (
            <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-slate-700">
              {expandedBody}
            </pre>
          )}

          {item.kind === "research" ? (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-slate-500">
                Detailed reports are generated in each workspace; history stores a lightweight record of your runs.
              </p>
              {researchWorkspaceHref ? (
                <Link
                  href={researchWorkspaceHref}
                  className="inline-flex text-sm font-semibold text-teal-700 hover:text-teal-800 hover:underline"
                >
                  Open workspace →
                </Link>
              ) : null}
            </div>
          ) : null}

          {urls.length > 0 ? (
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Links</p>
              <ul className="mt-2 space-y-1.5">
                {urls.map((href) => (
                  <li key={href}>
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="break-all text-sm font-medium text-teal-700 underline decoration-teal-700/30 underline-offset-2 hover:text-teal-800"
                    >
                      {href}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

        </div>
      ) : null}
    </article>
  );
}
