import { useCallback, useRef } from "react";

type ChatInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  loading: boolean;
  placeholder?: string;
};

export function ChatInput({
  value,
  onChange,
  onSend,
  loading,
  placeholder = "Ask why a stock moved today…",
}: ChatInputProps) {
  const taRef = useRef<HTMLTextAreaElement | null>(null);

  const send = useCallback(() => {
    if (loading || !value.trim()) return;
    onSend();
    requestAnimationFrame(() => taRef.current?.focus());
  }, [loading, onSend, value]);

  return (
    <div className="border-t border-slate-200/90 bg-white/95 px-3 py-3 sm:px-4 sm:py-4">
      <div className="flex gap-2 sm:gap-3">
        <textarea
          ref={taRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder={placeholder}
          disabled={loading}
          rows={1}
          className="max-h-40 min-h-[44px] w-0 min-w-0 flex-1 resize-y rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm text-slate-900 shadow-inner placeholder:text-slate-400 focus:border-teal-500/40 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500/20 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={send}
          disabled={loading || !value.trim()}
          className="h-11 shrink-0 self-end rounded-2xl bg-slate-900 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 hover:shadow disabled:opacity-40"
        >
          Send
        </button>
      </div>
      <p className="mt-2 text-center text-[10px] text-slate-500 sm:text-left">
        Educational use only. Not financial advice.
      </p>
    </div>
  );
}
