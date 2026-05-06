"""
Prompt templates for Revati's module.

Every prompt enforces the safety contract:
  - Educational use only
  - Not financial advice
  - No direct buy/sell instructions
  - Cite only evidence provided in context
  - State "evidence insufficient" when data is missing
"""

from __future__ import annotations

# ── Safety block injected into every prompt ───────────────────────────────────

SAFETY_BLOCK = """
IMPORTANT INSTRUCTIONS:
- This response is for educational purposes only and is NOT financial advice.
- Do NOT give direct buy, sell, or hold instructions.
- Do NOT make personalised investment recommendations.
- Use ONLY the context provided below. Do not invent data.
- If the evidence provided is insufficient, state: "Evidence is insufficient to draw a conclusion."
- If citations (URLs) are provided, include them in your response.
"""

# ── News Sentiment ─────────────────────────────────────────────────────────────

NEWS_THEMES_PROMPT = """\
{safety}

You are a financial analyst reviewing recent news for the stock ticker: {ticker}.

Identify the 3 most important recurring themes from the headlines below.
Then write a 2-sentence market sentiment summary explaining the overall tone.

Rules:
- Themes must be short noun phrases (3-6 words each), e.g. "AI infrastructure spending".
- Summary must end with: "This is for educational purposes only."
- Return ONLY valid JSON — no markdown fences, no extra text.

JSON format:
{{"themes": ["...", "...", "..."], "summary": "..."}}

Headlines (with sentiment label):
{headlines}
"""

# ── Chatbot: stock movement explanation ───────────────────────────────────────

STOCK_EXPLANATION_PROMPT = """\
{safety}

You are an educational stock market analyst.

User question: "{query}"

Recent news context for {ticker}:
{news_context}

Sentiment snapshot:
- Positive: {positive}%  Neutral: {neutral}%  Negative: {negative}%
- Detected themes: {themes}

Instructions:
1. Explain in plain English why {ticker} might be moving, citing the news context above.
2. List exactly 3 bullet-point reasons (short, specific).
3. Do NOT recommend buying, selling, or any action.
4. End the answer with: "This is for educational purposes only and is not financial advice."

Return ONLY valid JSON — no markdown fences, no extra text:
{{"answer": "...", "bullets": ["...", "...", "..."]}}
"""

# ── Chatbot: sentiment question ────────────────────────────────────────────────

SENTIMENT_QUESTION_PROMPT = """\
{safety}

You are an educational market analyst.

User question: "{query}"

Sentiment snapshot for {ticker}:
- {positive}% positive, {neutral}% neutral, {negative}% negative across {n_articles} articles.
- Top themes: {themes}
- Sample headlines: {headlines}

Instructions:
1. Explain the current sentiment picture for {ticker} in 2-3 sentences.
2. List exactly 3 key observations as bullet points.
3. Do NOT give buy/sell recommendations.
4. End with: "This is for educational purposes only and is not financial advice."

Return ONLY valid JSON — no markdown fences, no extra text:
{{"answer": "...", "bullets": ["...", "...", "..."]}}
"""

# ── Chatbot: comparison question ───────────────────────────────────────────────

COMPARISON_PROMPT = """\
{safety}

You are an educational market analyst.

User question: "{query}"

Tickers mentioned: {tickers}

Instructions:
1. Compare the tickers on publicly known dimensions (sector, market cap tier, growth vs value).
2. Note 3 key differences as bullet points.
3. Do NOT tell the user which ticker to buy or which is "better".
4. End with: "This is for educational purposes only and is not financial advice."

Return ONLY valid JSON — no markdown fences, no extra text:
{{"answer": "...", "bullets": ["...", "...", "..."]}}
"""

# ── Chatbot: general finance question ─────────────────────────────────────────

GENERAL_FINANCE_PROMPT = """\
{safety}

You are an educational financial analyst assistant.

User question: "{query}"

Instructions:
1. Answer the question clearly and factually in 2-3 sentences.
2. Provide 3 key points as bullet points.
3. Do NOT give personalised investment advice.
4. End with: "This is for educational purposes only and is not financial advice."

Return ONLY valid JSON — no markdown fences, no extra text:
{{"answer": "...", "bullets": ["...", "...", "..."]}}
"""


def build_news_themes_prompt(ticker: str, headlines: str) -> str:
    return NEWS_THEMES_PROMPT.format(
        safety=SAFETY_BLOCK,
        ticker=ticker.upper(),
        headlines=headlines,
    )


def build_stock_explanation_prompt(
    query: str,
    ticker: str,
    news_context: str,
    positive: int,
    neutral: int,
    negative: int,
    themes: str,
) -> str:
    return STOCK_EXPLANATION_PROMPT.format(
        safety=SAFETY_BLOCK,
        query=query,
        ticker=ticker,
        news_context=news_context,
        positive=positive,
        neutral=neutral,
        negative=negative,
        themes=themes,
    )


def build_sentiment_question_prompt(
    query: str,
    ticker: str,
    positive: int,
    neutral: int,
    negative: int,
    n_articles: int,
    themes: str,
    headlines: str,
) -> str:
    return SENTIMENT_QUESTION_PROMPT.format(
        safety=SAFETY_BLOCK,
        query=query,
        ticker=ticker,
        positive=positive,
        neutral=neutral,
        negative=negative,
        n_articles=n_articles,
        themes=themes,
        headlines=headlines,
    )


def build_comparison_prompt(query: str, tickers: str) -> str:
    return COMPARISON_PROMPT.format(
        safety=SAFETY_BLOCK,
        query=query,
        tickers=tickers,
    )


def build_general_finance_prompt(query: str) -> str:
    return GENERAL_FINANCE_PROMPT.format(
        safety=SAFETY_BLOCK,
        query=query,
    )


# ── Buy/Sell LLM explanation ───────────────────────────────────────────────────

BUY_SELL_EXPLANATION_PROMPT = """\
{safety}

You are an educational financial analyst explaining a deterministic scoring model's output.

Ticker: {ticker}
Deterministic Recommendation: {recommendation}
Overall Score: {overall_score}/100

Dimension Scores (rule-based, not your opinion):
- Fundamental: {fundamental_score}/100
- Technical:   {technical_score}/100
- Sentiment:   {sentiment_score}/100

Key signals from the data:
{signals}

Instructions:
1. In 3-4 sentences, explain in plain English what drove this deterministic score.
2. Reference ONLY the signals listed above — do NOT invent new data.
3. Do NOT make an independent buy/sell recommendation — just explain the model's output.
4. End with: "This is for educational purposes only and is not financial advice."

Return ONLY plain text (no JSON, no markdown fences).
"""


def build_buy_sell_explanation_prompt(
    ticker: str,
    recommendation: str,
    overall_score: int,
    fundamental_score: int,
    technical_score: int,
    sentiment_score: int,
    signals: list[str],
) -> str:
    signals_text = "\n".join(f"- {s}" for s in signals) if signals else "- No specific signals available."
    return BUY_SELL_EXPLANATION_PROMPT.format(
        safety=SAFETY_BLOCK,
        ticker=ticker.upper(),
        recommendation=recommendation,
        overall_score=overall_score,
        fundamental_score=fundamental_score,
        technical_score=technical_score,
        sentiment_score=sentiment_score,
        signals=signals_text,
    )


# ── Fundamental LLM explanation ────────────────────────────────────────────────

FUNDAMENTAL_EXPLANATION_PROMPT = """\
{safety}

You are an educational financial analyst explaining a rule-based fundamental analysis.

Ticker: {ticker}
Rule-based Verdict: {verdict}

Metrics extracted from public filings:
{metrics_text}

Strengths identified by rule engine:
{strengths_text}

Risks identified by rule engine:
{risks_text}

Instructions:
1. Write 3-4 sentences explaining this company's financial health in plain English.
2. Cite ONLY the metrics and signals listed above — do NOT invent figures.
3. Do NOT make investment recommendations.
4. End with: "This is for educational purposes only and is not financial advice."

Return ONLY plain text (no JSON, no markdown fences).
"""


def build_fundamental_explanation_prompt(
    ticker: str,
    verdict: str,
    metrics: dict,
    strengths: list[str],
    risks: list[str],
) -> str:
    metrics_lines = [
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in metrics.items() if v is not None
    ]
    metrics_text = "\n".join(metrics_lines) if metrics_lines else "- Metrics not available."
    strengths_text = "\n".join(f"- {s}" for s in strengths) if strengths else "- None flagged."
    risks_text = "\n".join(f"- {r}" for r in risks) if risks else "- None flagged."
    return FUNDAMENTAL_EXPLANATION_PROMPT.format(
        safety=SAFETY_BLOCK,
        ticker=ticker.upper(),
        verdict=verdict,
        metrics_text=metrics_text,
        strengths_text=strengths_text,
        risks_text=risks_text,
    )


# ── Multi-model comparison ─────────────────────────────────────────────────────

MULTI_MODEL_TASK_PROMPT = """\
{safety}

You are an educational financial analyst. Task: {task_label}

Ticker: {ticker}
Query: "{query}"

Focus area: {task_hint}

Instructions:
1. Provide a clear, factual 3-4 sentence response to the query.
2. List exactly 3 key observations as bullet points.
3. Do NOT give direct buy/sell recommendations.
4. End with: "This is for educational purposes only and is not financial advice."

Return ONLY valid JSON — no markdown fences, no extra text:
{{"answer": "...", "bullets": ["...", "...", "..."]}}
"""

_TASK_HINTS = {
    "chat": "general market analysis and stock information",
    "sentiment": "news tone, analyst views, and recent market sentiment",
    "buy_sell": "technical momentum, valuation signals, and risk/reward profile",
    "fundamental": "financial metrics, profitability, revenue growth, and balance sheet health",
}


def build_multi_model_comparison_prompt(task: str, ticker: str, query: str) -> str:
    hint = _TASK_HINTS.get(task, "general financial analysis")
    return MULTI_MODEL_TASK_PROMPT.format(
        safety=SAFETY_BLOCK,
        task_label=task.replace("_", " ").title(),
        ticker=ticker.upper(),
        query=query,
        task_hint=hint,
    )
