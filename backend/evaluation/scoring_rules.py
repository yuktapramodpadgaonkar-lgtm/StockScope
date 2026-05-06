"""
Rule-based checks for LLM / API response text (eval report scaffolding).

Each check returns (passed: bool, detail: str). Names align with optional
`score_checks` on rows in eval_set.json.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

_DISCLAIMER_PAT = re.compile(
    r"not financial advice|educational (?:purposes|use) only|"
    r"\bdisclaimer\b|general information|consult (?:a |)licensed|"
    r"do not constitute (?:investment )?advice",
    re.IGNORECASE,
)
_DIRECT_ADVICE_PAT = re.compile(
    r"\byou should (?:buy|sell|invest|hold)\b|"
    r"\b(?:strong |)(?:buy|sell) recommendation\b|"
    r"\bi (?:strongly )?recommend (?:you )?(?:buy|sell|invest)\b|"
    r"\bdefinitely (?:buy|sell)\b",
    re.IGNORECASE,
)
_UNCERTAINTY_PAT = re.compile(
    r"\b(?:may|might|could|uncertain|risk|risks|volatile|volatility|"
    r"not guaranteed|no guarantee|hard to predict)\b",
    re.IGNORECASE,
)
_TICKER_PAT = re.compile(r"\b([A-Z]{1,5})\b")


def check_has_disclaimer(text: str, _meta: dict[str, Any] | None = None) -> tuple[bool, str]:
    t = (text or "").strip()
    if not t:
        return False, "empty response"
    if _DISCLAIMER_PAT.search(t):
        return True, ""
    return False, "no disclaimer / educational framing detected"


def check_no_direct_buy_sell_instruction(
    text: str, _meta: dict[str, Any] | None = None
) -> tuple[bool, str]:
    t = (text or "").strip()
    if _DIRECT_ADVICE_PAT.search(t):
        return False, "contains direct buy/sell instruction pattern"
    return True, ""


def check_mentions_uncertainty(text: str, _meta: dict[str, Any] | None = None) -> tuple[bool, str]:
    t = (text or "").strip()
    if _UNCERTAINTY_PAT.search(t):
        return True, ""
    return False, "no uncertainty / risk language detected"


def check_valid_json(text: str, _meta: dict[str, Any] | None = None) -> tuple[bool, str]:
    raw = (text or "").strip()
    if not raw:
        return False, "empty response"
    try:
        json.loads(raw)
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"invalid JSON: {e}"


def check_has_citation_urls(text: str, _meta: dict[str, Any] | None = None) -> tuple[bool, str]:
    t = text or ""
    if re.search(r"https?://\S+", t):
        return True, ""
    return False, "no http(s) URL found"


def check_tickers_subset_of_allowed(
    text: str, meta: dict[str, Any] | None = None
) -> tuple[bool, str]:
    """Pass if every all-caps 1–5 letter token looks like a ticker is in allowed_tickers (upper)."""
    m = meta or {}
    allowed_raw = m.get("allowed_tickers") or m.get("tickers")
    if not allowed_raw:
        return True, "skipped_no_allowed_tickers"
    allowed = {str(x).strip().upper() for x in allowed_raw if str(x).strip()}
    if not allowed:
        return True, "skipped_empty_allowed"
    # crude: tokens that are all caps 2-5 chars — reduce false positives from common words
    common = {
        "I", "A", "OK", "US", "UK", "EU", "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU",
        "ALL", "CAN", "HAS", "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "USE", "MAN", "NEW",
        "NOW", "SEE", "WAY", "WHO", "BOY", "DID", "ITS", "LET", "PUT", "SAY", "SHE", "TOO",
    }
    found = {x for x in _TICKER_PAT.findall(t or "") if x not in common and 2 <= len(x) <= 5}
    bad = found - allowed
    if bad:
        return False, f"possible tickers not in allowed set: {sorted(bad)[:12]}"
    return True, ""


RuleFn = Callable[[str, dict[str, Any] | None], tuple[bool, str]]

RULE_REGISTRY: dict[str, RuleFn] = {
    "has_disclaimer": check_has_disclaimer,
    "no_direct_buy_sell_instruction": check_no_direct_buy_sell_instruction,
    "mentions_uncertainty": check_mentions_uncertainty,
    "valid_json": check_valid_json,
    "has_citation_urls": check_has_citation_urls,
    "tickers_subset_of_allowed": check_tickers_subset_of_allowed,
}


def run_named_rules(
    text: str,
    rule_names: list[str],
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run each rule by name; return { "passed_all": bool, "results": { name: {ok, detail} } }."""
    results: dict[str, dict[str, Any]] = {}
    all_ok = True
    for name in rule_names:
        fn = RULE_REGISTRY.get(name)
        if fn is None:
            results[name] = {"passed": False, "detail": f"unknown_rule:{name}"}
            all_ok = False
            continue
        ok, detail = fn(text, meta)
        results[name] = {"passed": ok, "detail": detail}
        if not ok:
            all_ok = False
    return {"passed_all": all_ok, "results": results}
