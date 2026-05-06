export function LoadingTypingIndicator() {
  return (
    <div
      className="max-w-[90%] rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 shadow-sm"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="inline-flex items-center gap-1.5">
        <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
        <span className="ml-2 text-xs font-medium text-slate-500">Assistant is typing…</span>
      </div>
    </div>
  );
}
