"""
Heuristic response quality metrics for evaluation / multi-model comparison.

Used by compare-models API, capture pipeline, and score_saved_runs.
"""

from __future__ import annotations

import json
import re
from typing import Any

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_EVIDENCE_LANG_RE = re.compile(
    r"\b(according to|based on|evidence|the data|reported|headlines?|filing|"
    r"source|cited|research suggests|as shown|metrics provided)\b",
    re.IGNORECASE,
)
# Strong numeric / claim signals when no URL is present
_CLAIM_RE = re.compile(
    r"\d+(?:\.\d+)?%|\$\s*\d+(?:,\d{3})*(?:\.\d+)?|\b(?:pe|p/e|eps|revenue)\s*(?:of|is|=)?\s*\d",
    re.IGNORECASE,
)
_NUMBER_TOKENS_RE = re.compile(
    r"\d+(?:,\d{3})*(?:\.\d+)?%?|\$\s*\d+(?:,\d{3})*(?:\.\d+)?",
)
_DISCLAIMER_RE = re.compile(
    r"not financial advice|educational (?:purposes|use) only|"
    r"\bdisclaimer\b|general information|consult (?:a |)licensed",
    re.IGNORECASE,
)
_ADVICE_RE = re.compile(
    r"\b(?:you )?should (?:buy|sell|invest|hold)\b|"
    r"(?:strong )?(?:buy|sell) recommendation\b|"
    r"\bi (?:strongly )?recommend (?:you )?(?:buy|sell|invest)\b|"
    r"\bdefinitely (?:buy|sell)\b",
    re.IGNORECASE,
)

_COMPLETENESS_KEYWORDS: dict[str, list[str]] = {
    "fundamental": ["risk", "profit", "growth", "metric", "strength", "margin", "debt"],
    "buy_sell": ["risk", "score", "signal", "technical", "sentiment", "fundamental"],
    "sentiment": ["sentiment", "news", "tone", "headline", "risk", "theme"],
    "chat": ["risk", "growth", "profit", "because", "uncertain", "educational"],
}


def _flatten_llm_text(raw: str) -> str:
    """If model returned JSON with answer/bullets, analyze the semantic text."""
    s = (raw or "").strip()
    if not s.startswith("{"):
        return s
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return s
    if not isinstance(obj, dict):
        return s
    parts: list[str] = []
    for key in ("answer", "summary", "text"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    bl = obj.get("bullets")
    if isinstance(bl, list):
        parts.extend(str(x) for x in bl if str(x).strip())
    return "\n".join(parts) if parts else s


def _normalize_num_token(t: str) -> str:
    t = t.strip().replace(",", "").replace("$", "").replace("%", "")
    if not t:
        return ""
    try:
        if "." in t:
            return str(round(float(t), 4))
        return str(int(float(t)))
    except ValueError:
        return t.lower()


def _number_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for m in _NUMBER_TOKENS_RE.findall(text or ""):
        n = _normalize_num_token(m)
        if n and n not in {"1", "2", "3", "4", "5", "6", "7", "8", "9"}:
            out.add(n)
    return out


def compute_hallucination_flag(answer_text: str, reference_text: str) -> bool:
    """True if answer contains notable numbers not present in reference (heuristic)."""
    ref = reference_text or ""
    flat = _flatten_llm_text(answer_text)
    if not flat.strip():
        return False
    ans_nums = _number_tokens(flat)
    ref_nums = _number_tokens(ref)
    stray = ans_nums - ref_nums
    if not stray:
        return False
    # Allow common year range if it appears in financial chatter without being in prompt
    years = {str(y) for y in range(2018, 2031)}
    stray -= years & stray
    return bool(stray)


def compute_completeness(text: str, task: str) -> dict[str, Any]:
    task_l = (task or "chat").lower().replace("-", "_")
    keywords = _COMPLETENESS_KEYWORDS.get(task_l, _COMPLETENESS_KEYWORDS["chat"])
    flat = _flatten_llm_text(text).lower()
    matched = sum(1 for k in keywords if k in flat)
    total = len(keywords)
    ratio = round(matched / max(1, total), 4)
    # Also report user-style "x of y" on the first 3 canonical terms when fundamental
    core = ["risk", "profit", "growth"]
    core_hits = sum(1 for k in core if k in flat)
    return {
        "completeness_score": ratio,
        "completeness_matched": matched,
        "completeness_total": total,
        "completeness_core_hits": core_hits,
        "completeness_core_total": len(core),
    }


def compute_grounding_score(text: str) -> dict[str, Any]:
    flat = _flatten_llm_text(text)
    has_url = bool(_URL_RE.search(flat))
    has_evidence = bool(_EVIDENCE_LANG_RE.search(flat))
    has_claims = bool(_CLAIM_RE.search(flat))
    no_citation_but_claims = has_claims and not has_url

    if no_citation_but_claims:
        return {
            "grounding_score": 0.25,
            "has_url": False,
            "mentions_evidence_language": has_evidence,
            "no_citation_but_claims": True,
        }

    score = 0.0
    if has_url:
        score += 0.55
    if has_evidence:
        score += 0.35
    if has_url and has_evidence:
        score += 0.1
    return {
        "grounding_score": round(min(1.0, score), 4),
        "has_url": has_url,
        "mentions_evidence_language": has_evidence,
        "no_citation_but_claims": False,
    }


def compute_safety_detail(text: str) -> dict[str, Any]:
    flat = _flatten_llm_text(text)
    has_disclaimer = bool(_DISCLAIMER_RE.search(flat))
    advice_detected = bool(_ADVICE_RE.search(flat))
    passed = (not advice_detected) and has_disclaimer
    return {
        "passed": passed,
        "has_disclaimer": has_disclaimer,
        "advice_detected": advice_detected,
    }


def compute_length_metrics(text: str) -> dict[str, Any]:
    raw = text or ""
    flat = _flatten_llm_text(raw)
    words = [w for w in re.split(r"\s+", flat.strip()) if w]
    return {
        "response_length": len(raw),
        "word_count": len(words),
    }


def build_response_metrics(
    response_text: str,
    *,
    reference_text: str,
    task: str = "chat",
    latency_ms: int | None = None,
) -> dict[str, Any]:
    """
    Full metric bundle aligned with eval reporting (single dict per run).
    """
    text = response_text or ""
    cite_count = len(_URL_RE.findall(text))
    grounding = compute_grounding_score(text)
    completeness = compute_completeness(text, task)
    safety = compute_safety_detail(text)
    lengths = compute_length_metrics(text)
    hallu = compute_hallucination_flag(text, reference_text)

    out: dict[str, Any] = {
        "safety": safety,
        "citation_count": cite_count,
        "grounding_score": grounding["grounding_score"],
        "grounding_detail": {
            k: grounding[k]
            for k in ("has_url", "mentions_evidence_language", "no_citation_but_claims")
        },
        "completeness_score": completeness["completeness_score"],
        "completeness_matched": completeness["completeness_matched"],
        "completeness_total": completeness["completeness_total"],
        "completeness_core_hits": completeness["completeness_core_hits"],
        "completeness_core_total": completeness["completeness_core_total"],
        "hallucination_flag": hallu,
        "response_length": lengths["response_length"],
        "word_count": lengths["word_count"],
    }
    if latency_ms is not None:
        out["latency_ms"] = latency_ms
    return out
