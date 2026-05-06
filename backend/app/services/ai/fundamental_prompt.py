"""Build prompts for optional LLM explanation of deterministic fundamental reports."""

from __future__ import annotations

import json


def _few_report() -> str:
    from services.ai.few_shot_loader import few_shot_examples_block

    block = few_shot_examples_block("fundamental_report")
    return f"\n{block}\n" if block else ""


def build_fundamental_prompt(report: dict) -> str:
    """
    Turn a deterministic fundamental report dict into a user prompt for the LLM.
    The model must only explain what is already in the JSON — no new numbers or facts.
    """
    payload = json.dumps(report, indent=2, default=str)

    return f"""You are helping a beginner understand a stock research snapshot. Your job is to explain ONLY what appears in the JSON below.
{_few_report()}
Rules (must follow):
- Use ONLY information present in the JSON. Do not invent metrics, prices, dates, or company facts.
- Do not quote or make up specific numbers except those explicitly given in the JSON (you may restate them in plain language).
- Do NOT tell the reader to buy, sell, or hold. No personalized financial advice. No recommendations.
- Briefly summarize what the snapshot suggests in plain English: 2–4 short paragraphs OR a few bullet sections, total under ~250 words.
- Cover strengths and risks using the provided "strengths" and "risks" lists and the metrics in a beginner-friendly way (define jargon lightly if needed).
- Tone: educational and cautious. Mention that this is for learning, data can be wrong or stale, and people should verify independently — similar to an educational disclaimer.

JSON report:
{payload}

Now write your concise educational explanation following the rules above."""


def build_fundamental_repair_prompt(*, report: dict, previous_text: str, problem: str) -> str:
    """
    Second-pass rewrite: remove unsupported numeric/factual claims.
    """
    payload = json.dumps(report, indent=2, default=str)
    prev = (previous_text or "").strip()
    if len(prev) > 1800:
        prev = prev[:1800] + "…"
    return f"""You are rewriting an educational explanation of a stock fundamentals snapshot.

Problem: {problem}

Rules (must follow):
- Use ONLY information present in the JSON below. Do not invent metrics, prices, dates, or company facts.
- Do not quote or make up specific numbers except those explicitly given in the JSON.
- Do NOT tell the reader to buy, sell, or hold. No personalized financial advice. No recommendations.
- Keep it concise (under ~200 words).

Previous explanation (contains issues; fix it):
{prev}

JSON report:
{payload}

Now rewrite the explanation to fix the problem. Output plain text only (no JSON)."""
