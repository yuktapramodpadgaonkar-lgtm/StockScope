import { HistoryCard } from "@/components/history/HistoryCard";
import { EmptyState } from "@/components/history/EmptyState";
import type { UnifiedHistoryItem } from "@/components/history/historyUtils";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";

type HistoryListProps = {
  items: UnifiedHistoryItem[];
  loading: boolean;
  emptyState: { title: string; description: string };
  filteredEmptyMessage: { title: string; description: string };
  hasActiveFilters: boolean;
};

function HistoryListSkeleton() {
  return (
    <div className="grid gap-4" aria-busy="true" aria-label="Loading history">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm"
        >
          <div className="flex gap-3">
            <LoadingSkeleton className="h-7 w-20 rounded-full" />
            <LoadingSkeleton className="h-7 w-16 rounded-lg" />
          </div>
          <LoadingSkeleton className="mt-4 h-5 w-3/4" />
          <LoadingSkeleton className="mt-2 h-3 w-40" />
          <LoadingSkeleton className="mt-3 h-4 w-full" />
          <LoadingSkeleton className="mt-1 h-4 w-5/6" />
        </div>
      ))}
    </div>
  );
}

export function HistoryList({
  items,
  loading,
  emptyState,
  filteredEmptyMessage,
  hasActiveFilters,
}: HistoryListProps) {
  if (loading) {
    return <HistoryListSkeleton />;
  }

  if (items.length === 0) {
    const copy = hasActiveFilters ? filteredEmptyMessage : emptyState;
    return <EmptyState title={copy.title} description={copy.description} />;
  }

  return (
    <div className="grid gap-4">
      {items.map((item) => {
        const key =
          item.kind === "chat"
            ? `chat-${item.data.thread_id}`
            : item.kind === "research"
              ? `research-${item.data.id}`
              : `prompt-${item.data.id}`;
        return <HistoryCard key={key} item={item} />;
      })}
    </div>
  );
}
