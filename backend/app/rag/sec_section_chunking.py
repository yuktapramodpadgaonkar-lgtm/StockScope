"""
Section-aware chunking for SEC EDGAR HTML filings (10-K / 10-Q).

Replaces blind fixed-size slicing so queries like "What risks did the company disclose?"
can retrieve Risk Factors (Item 1A) instead of an arbitrary 4000-character window.
"""

from __future__ import annotations

import html as html_lib
import re
from typing import Any

# Block boundaries → newlines before tag stripping (helps "Item 1A." fall at line start).
_BLOCK_END = re.compile(
    r"(?is)</\s*(?:p|div|h[1-6]|tr|table|li|td|th|section|font)\s*>",
)
_BR = re.compile(r"(?i)<\s*br\s*/?\s*>")
_SCRIPT_STYLE = re.compile(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>")
_TAGS = re.compile(r"<[^>]+>")

# Item line: "Item 1A." or "ITEM 7." optional rest of title on same line.
_ITEM_LINE = re.compile(
    r"(?im)^[ \t]*item[ \t]+(\d+[a-z]?)[ \t]*[.:]?[ \t]*(.*)$",
)

# Subsections inside MD&A (Item 7) — separate retrievable slices when the heading is on its own line.
_MDNA_SUB = re.compile(
    r"(?im)^[ \t]*(?P<head>"
    r"liquidity\s+and\s+capital\s+resources"
    r"|capital\s+resources\s+and\s+liquidity"
    r")\b[ \t]*[.:]?[ \t]*$",
)

_ITEM_TO_KEY: dict[str, str] = {
    "1": "business",
    "1A": "risk_factors",
    "1B": "unresolved_staff_comments",
    "2": "properties",
    "3": "legal_proceedings",
    "4": "mine_safety",  # rare in issuers we care about
    "5": "market_registrant",
    "6": "exhibits_summary",
    "7": "mdna",
    "7A": "market_risk",
    "8": "financial_statements",
    "9": "financial_statement_changes",
    "9A": "controls_procedures",
    "9B": "other_information",
    "10": "directors_officers",
    "11": "executive_compensation",
    "12": "security_ownership",
    "13": "certain_relationships",
    "14": "principal_accountant",
    "15": "exhibits_signatures",
}


def html_to_line_oriented_plain_text(content: bytes) -> str:
    """Strip HTML but preserve line breaks roughly where block elements end."""
    s = content.decode("utf-8", errors="ignore")
    s = _SCRIPT_STYLE.sub(" ", s)
    s = _BR.sub("\n", s)
    s = _BLOCK_END.sub("\n", s)
    s = _TAGS.sub(" ", s)
    s = html_lib.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _canonical_key(item_code: str) -> str:
    c = item_code.upper()
    return _ITEM_TO_KEY.get(c, f"item_{c.lower()}")


def _human_title(item_code: str, rest_of_line: str) -> str:
    rest = (rest_of_line or "").strip()
    if len(rest) >= 3:
        t = rest[:120]
        if len(rest) > 120:
            t += "…"
        return f"Item {item_code.upper()} — {t}"
    labels = {
        "1": "Business",
        "1A": "Risk Factors",
        "3": "Legal Proceedings",
        "7": "MD&A",
        "7A": "Market Risk",
        "8": "Financial Statements",
    }
    lab = labels.get(item_code.upper(), "")
    if lab:
        return f"Item {item_code.upper()} — {lab}"
    return f"Item {item_code.upper()}"


def split_filing_text_by_items(plain_text: str) -> list[dict[str, Any]]:
    """
    Split 10-K/10-Q plain text at SEC Item headers.
    Returns list of dicts: section_key, item_code, title, text.
    """
    text = plain_text.strip()
    matches = list(_ITEM_LINE.finditer(text))
    if len(matches) < 2:
        return []

    out: list[dict[str, Any]] = []
    for i, m in enumerate(matches):
        code = m.group(1).upper()
        rest = m.group(2) or ""
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # Keep the Item header line in `text` so queries like "risk factors" / "Item 1A" match.
        body = text[start:end].strip()
        if len(body) < 40:
            continue
        out.append(
            {
                "section_key": _canonical_key(code),
                "item_code": code,
                "title": _human_title(code, rest),
                "text": body,
            }
        )
    return out


def _subsplit_mdna(section: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull Liquidity / capital resources slice out of MD&A when clearly marked."""
    if section.get("section_key") != "mdna":
        return [section]
    body = section.get("text") or ""
    if len(body) < 2500:
        return [section]

    m = _MDNA_SUB.search(body)
    if not m or m.start() < 100:
        return [section]

    before = body[: m.start()].strip()
    liquidity_block = body[m.start() :].strip()
    if len(liquidity_block) < 400:
        return [section]

    chunks: list[dict[str, Any]] = []
    if len(before) >= 200:
        chunks.append(
            {
                **{k: v for k, v in section.items() if k != "text"},
                "section_key": "mdna",
                "title": section.get("title", "Item 7 — MD&A").replace("MD&A", "MD&A (overview)"),
                "text": before,
            }
        )
    head = m.group("head") or "Liquidity"
    chunks.append(
        {
            "section_key": "liquidity",
            "item_code": section.get("item_code"),
            "title": f"Item {section.get('item_code') or '7'} — {head.title()}",
            "text": liquidity_block,
        }
    )
    return chunks


def extract_sections_from_sec_html(html_bytes: bytes) -> list[dict[str, Any]]:
    """
    Parse SEC filing HTML into section dicts suitable for RAG chunk rows.
    Returns [] if structure is not recognized (caller should fall back to flat text).
    """
    plain = html_to_line_oriented_plain_text(html_bytes)
    sections = split_filing_text_by_items(plain)
    if not sections:
        return []

    expanded: list[dict[str, Any]] = []
    for sec in sections:
        expanded.extend(_subsplit_mdna(sec))
    return expanded


def sections_to_flat_text(sections: list[dict[str, Any]]) -> str:
    """Single document string for legacy consumers."""
    parts: list[str] = []
    for s in sections:
        parts.append(f"{s.get('title') or s.get('section_key')}\n{s.get('text') or ''}")
    return "\n\n".join(parts)
