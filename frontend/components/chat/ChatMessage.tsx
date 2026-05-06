import { CitationList } from "@/components/chat/CitationList";
import { formatMessageTime, isRichAssistantPayload } from "@/components/chat/chatUtils";
import type { ChatQueryResponse } from "@/lib/revati-types";

export type ChatMessageModel =
  | { role: "user"; text: string; at: string }
  | { role: "assistant"; payload: ChatQueryResponse; at: string };

type ChatMessageProps = {
  message: ChatMessageModel;
};

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] space-y-1">
          <div className="rounded-2xl rounded-br-md bg-slate-900 px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
            {message.text}
          </div>
          <p className="pr-1 text-right text-[10px] text-slate-500">{formatMessageTime(message.at)}</p>
        </div>
      </div>
    );
  }

  const { payload, at } = message;
  const rich = isRichAssistantPayload(payload);
  const tickers = payload.tickers ?? [];
  const bullets = payload.summary_bullets ?? [];
  const citations = payload.citations ?? [];

  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] space-y-1">
        <div className="rounded-2xl rounded-bl-md border border-slate-200/90 bg-white px-4 py-3 shadow-sm">
          {rich ? (
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              Intent · <span className="text-slate-700">{payload.detected_intent.replace(/_/g, " ")}</span>
            </p>
          ) : null}
          {tickers.length > 0 ? (
            <p className="mt-1 text-xs font-medium text-slate-600">Tickers: {tickers.join(", ")}</p>
          ) : null}
          <p className={`text-sm leading-relaxed text-slate-800 ${rich ? "mt-2" : ""}`}>{payload.answer ?? ""}</p>
          {bullets.length > 0 ? (
            <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-slate-600">
              {bullets.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          ) : null}
          <CitationList citations={citations} answerText={payload.answer} />
          {payload.disclaimer ? (
            <p className="mt-2 text-[10px] leading-snug text-slate-400">{payload.disclaimer}</p>
          ) : null}
        </div>
        <p className="pl-1 text-[10px] text-slate-500">{formatMessageTime(at)}</p>
      </div>
    </div>
  );
}
