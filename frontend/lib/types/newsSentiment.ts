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

export type CitationItem = {
  title: string;
  url: string;
  source: string;
  published_at: string;
};

export type NewsSentimentResponse = {
  ticker: string;
  date_from: string | null;
  date_to: string | null;
  aggregate_sentiment: AggregateSentiment;
  major_themes: string[];
  articles: NewsArticleItem[];
  summary: string;
  citations: CitationItem[];
  disclaimer: string;
  fallback_used: boolean;
};
