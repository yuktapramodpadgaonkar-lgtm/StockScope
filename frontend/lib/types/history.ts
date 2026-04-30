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
