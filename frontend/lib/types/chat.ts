export type ChatIntent =
  | "stock_explanation"
  | "sentiment_question"
  | "comparison_question"
  | "history_lookup"
  | "financial_advice_rejected"
  | "unknown";

export type ChatCitation = {
  title: string;
  url: string;
  source: string;
  published_at: string;
};

export type ChatQueryRequest = {
  query: string;
  thread_id?: string | null;
};

export type ChatQueryResponse = {
  thread_id: string;
  detected_intent: ChatIntent;
  tickers: string[];
  answer: string;
  summary_bullets: string[];
  citations: ChatCitation[];
  disclaimer: string;
  timestamp: string;
  llm_model_used: string | null;
  llm_provider: string | null;
  llm_fallback_used: boolean;
};
