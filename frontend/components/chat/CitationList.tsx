import { extractUrls } from "@/components/history/historyUtils";
import type { ChatCitation } from "@/lib/revati-types";

type CitationListProps = {
  citations?: ChatCitation[] | null;
  /** Extra plain text (e.g. answer) to pull http(s) links from */
  answerText?: string;
};

export function CitationList({ citations, answerText = "" }: CitationListProps) {
  const safeCitations = citations ?? [];
  const fromAnswer = extractUrls(answerText);
  const citationUrls = new Set(safeCitations.map((c) => c.url));
  const extraUrls = fromAnswer.filter((u) => !citationUrls.has(u));

  if (safeCitations.length === 0 && extraUrls.length === 0) return null;

  return (
    <div className="mt-3 rounded-xl border border-slate-200/90 bg-slate-50/90 px-3 py-2.5">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Sources</p>
      <ul className="mt-2 space-y-2">
        {safeCitations.map((c, idx) => (
          <li key={`${c.url}-${idx}`} className="text-xs">
            <a
              href={c.url}
              className="font-medium text-teal-700 underline decoration-teal-600/30 underline-offset-2 transition hover:text-teal-800"
              target="_blank"
              rel="noopener noreferrer"
            >
              {c.title}
            </a>
            <span className="text-slate-500"> · {c.source}</span>
          </li>
        ))}
        {extraUrls.map((href) => (
          <li key={href}>
            <a
              href={href}
              className="break-all text-xs font-medium text-teal-700 underline decoration-teal-600/30 underline-offset-2 hover:text-teal-800"
              target="_blank"
              rel="noopener noreferrer"
            >
              {href}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
