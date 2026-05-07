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
  model_used: string | null;
  provider: string | null;
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

export type ThreadMessage = {
  role: string;
  text: string;
  timestamp: string;
  intent: string | null;
  model_used: string | null;
  provider: string | null;
  fallback_used: boolean | null;
};

export type ThreadHistoryResponse = {
  thread_id: string;
  messages: ThreadMessage[];
};

/** Session long-horizon memory (style hints; not investment advice). */
export type MemorySummaryResponse = {
  session_id: string;
  frequent_tickers: string[];
  preferred_topics: string[];
  risk_style: string | null;
  last_updated: string;
};
