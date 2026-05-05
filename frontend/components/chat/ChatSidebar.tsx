import type { ChatHistoryItem } from "@/lib/revati-types";

import { SuggestedPrompts } from "@/components/chat/SuggestedPrompts";
import { formatHistoryTimestamp } from "@/components/history/historyUtils";

type ChatSidebarProps = {
  threads: ChatHistoryItem[];
  activeThreadId: string;
  onSelectThread: (threadId: string) => void;
  onNewChat: () => void;
  onSuggestedPrompt: (text: string) => void;
  suggestedDisabled?: boolean;
  loading?: boolean;
};

export function ChatSidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onNewChat,
  onSuggestedPrompt,
  suggestedDisabled,
  loading,
}: ChatSidebarProps) {
  return (
    <aside className="flex w-full flex-col gap-5 rounded-2xl border border-slate-200/90 bg-white p-4 shadow-sm lg:max-w-[280px] lg:shrink-0">
      <div>
        <button
          type="button"
          onClick={onNewChat}
          className="w-full rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800"
        >
          New chat
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-2">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Recent chats</p>
        {loading ? (
          <p className="text-xs text-slate-400">Loading…</p>
        ) : threads.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-3 py-4 text-center">
            <p className="text-xs font-medium text-slate-600">No previous chats</p>
            <p className="mt-1 text-[11px] leading-relaxed text-slate-500">
              Start a conversation or run an analysis—threads will appear here.
            </p>
          </div>
        ) : (
          <ul className="max-h-[40vh] space-y-1 overflow-y-auto pr-0.5 lg:max-h-[min(50vh,360px)]">
            {threads.map((t) => {
              const active = activeThreadId === t.thread_id;
              return (
                <li key={t.thread_id}>
                  <button
                    type="button"
                    onClick={() => onSelectThread(t.thread_id)}
                    className={`w-full rounded-xl border px-3 py-2.5 text-left text-xs font-medium leading-snug transition ${
                      active
                        ? "border-teal-500/40 bg-teal-50 text-teal-900 shadow-sm"
                        : "border-slate-200/90 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <span className="line-clamp-2">{t.title || "Untitled"}</span>
                    <span className="mt-1 block text-[10px] font-normal text-slate-500">
                      {formatHistoryTimestamp(t.last_updated)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <SuggestedPrompts onSelect={onSuggestedPrompt} disabled={suggestedDisabled} />
    </aside>
  );
}
