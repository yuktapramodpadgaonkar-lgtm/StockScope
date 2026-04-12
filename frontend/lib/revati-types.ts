/**
 * Week 1 API contracts for chat, news sentiment, and history.
 * TODO: Align with OpenAPI codegen or shared schema when backend stabilizes.
 */

export type ChatIntent =
  | "stock_explanation"
  | "sentiment_question"
  | "comparison_question"
  | "unknown";

export type ChatCitation = {
  title: string;
  url: string;
  source: string;
  published_at: string;
};

export type ChatQueryResponse = {
  thread_id: string;
  detected_intent: ChatIntent;
  answer: string;
  summary_bullets: string[];
  citations: ChatCitation[];
  disclaimer: string;
  timestamp: string;
};

export type NewsSentimentLabel = "positive" | "neutral" | "negative";

export type AggregateSentiment = {
  positive: number;
  neutral: number;
  negative: number;
  overall_label: NewsSentimentLabel;
};

export type NewsArticleItem = {
  headline: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: NewsSentimentLabel;
  summary: string;
};

export type NewsSentimentResponse = {
  ticker: string;
  date_from: string | null;
  date_to: string | null;
  aggregate_sentiment: AggregateSentiment;
  major_themes: string[];
  articles: NewsArticleItem[];
  llm_summary: string;
  disclaimer: string;
};

export type ChatHistoryItem = {
  thread_id: string;
  title: string;
  last_updated: string;
};

export type ResearchHistoryItem = {
  id: string;
  type: string;
  ticker: string;
  created_at: string;
};

export type SavedPromptItem = {
  id: string;
  title: string;
  prompt_text: string;
};

export type HistoryResponse = {
  chat_history: ChatHistoryItem[];
  research_history: ResearchHistoryItem[];
  saved_prompts: SavedPromptItem[];
};
