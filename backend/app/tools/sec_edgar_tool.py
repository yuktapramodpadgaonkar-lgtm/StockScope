from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx
from lxml import html as lxml_html

from app.core.config import settings
from app.rag.sec_section_chunking import extract_sections_from_sec_html, sections_to_flat_text
from app.rag.store import RAG_DIR

SEC_TICKER_CACHE = RAG_DIR / "sec" / "company_tickers.json"


def _sec_headers() -> dict[str, str]:
    ua = (settings.sec_user_agent or "").strip()
    return {
        "User-Agent": ua,
        "Accept-Encoding": "gzip, deflate",
    }


def _www_headers() -> dict[str, str]:
    ua = (settings.sec_user_agent or "").strip()
    return {
        "User-Agent": ua,
        "Accept-Encoding": "gzip, deflate",
    }


def _cache_fresh(path: Path, hours: int) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < max(3600, hours * 3600)


def _load_ticker_to_cik() -> dict[str, int]:
    SEC_TICKER_CACHE.parent.mkdir(parents=True, exist_ok=True)
    hours = max(1, int(settings.sec_cik_cache_hours))
    url = "https://www.sec.gov/files/company_tickers.json"

    if not _cache_fresh(SEC_TICKER_CACHE, hours):
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            r = client.get(url, headers=_www_headers())
            r.raise_for_status()
            SEC_TICKER_CACHE.write_bytes(r.content)

    raw = json.loads(SEC_TICKER_CACHE.read_text(encoding="utf-8"))
    out: dict[str, int] = {}
    # SEC JSON is either {"0": {...}, ...} or list of dicts depending on version
    if isinstance(raw, dict):
        iterable = raw.values()
    else:
        iterable = raw
    for row in iterable:
        if not isinstance(row, dict):
            continue
        t = str(row.get("ticker") or "").strip().upper()
        cik = row.get("cik_str") or row.get("cik")
        if t and cik is not None:
            try:
                out[t] = int(cik)
            except (TypeError, ValueError):
                continue
    return out


def _accession_to_nodash(acc: str) -> str:
    return acc.replace("-", "")


def _html_to_text(content: bytes) -> str:
    try:
        tree = lxml_html.fromstring(content)
        parts = tree.xpath("//text()")
        text = " ".join(str(p).strip() for p in parts if str(p).strip())
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        return content.decode("utf-8", errors="ignore")[: settings.sec_filing_max_download_chars]


def _parse_filing_body(body: bytes, primary_document: str, content_type: str) -> tuple[str, list[dict[str, Any]] | None]:
    """
    HTML: try section-aware parse (10-K/10-Q Items); fall back to flat HTML text.
    Returns (flat_text_for_legacy, sections_or_none).
    """
    mx = max(10_000, int(settings.sec_filing_max_download_chars))
    if len(body) > mx:
        body = body[:mx]
    ctype = (content_type or "").lower()
    if "html" in ctype or primary_document.lower().endswith((".htm", ".html")):
        sections = extract_sections_from_sec_html(body)
        if sections:
            flat = sections_to_flat_text(sections)
            return flat[:mx], sections
        return _html_to_text(body)[:mx], None
    return body.decode("utf-8", errors="ignore")[:mx], None


def _fetch_filing_text(cik_int: int, accession: str, primary_document: str) -> str:
    text, _sections = _fetch_filing_text_and_sections(cik_int, accession, primary_document)
    return text


def _fetch_filing_text_and_sections(
    cik_int: int, accession: str, primary_document: str
) -> tuple[str, list[dict[str, Any]] | None]:
    acc_nd = _accession_to_nodash(accession)
    cik_part = str(int(cik_int))
    path = f"/Archives/edgar/data/{cik_part}/{acc_nd}/{primary_document}"
    url = f"https://www.sec.gov{path}"
    delay = max(0.0, float(settings.sec_request_delay_seconds))
    time.sleep(delay)
    with httpx.Client(timeout=90.0, follow_redirects=True) as client:
        r = client.get(url, headers=_www_headers())
        r.raise_for_status()
        body = r.content
        ctype = (r.headers.get("content-type") or "").lower()
    return _parse_filing_body(body, primary_document, ctype)


def fetch_recent_filings_bundle(ticker: str, *, limit: int = 3) -> tuple[dict[str, Any], int]:
    """
    Returns (bundle, http_call_count). SEC requires a descriptive User-Agent (set SEC_USER_AGENT).
    """
    sym = ticker.strip().upper()
    if not (settings.sec_user_agent or "").strip():
        return (
            {
                "ticker": sym,
                "source": "sec_edgar",
                "items": [],
                "error": "missing_user_agent",
                "note": "Set SEC_USER_AGENT in .env to a string that identifies you (SEC policy).",
            },
            0,
        )

    calls = 0
    try:
        cmap = _load_ticker_to_cik()
    except Exception as e:
        return (
            {
                "ticker": sym,
                "source": "sec_edgar",
                "items": [],
                "error": "cik_map_failed",
                "detail": str(e)[:300],
            },
            calls,
        )

    if sym not in cmap:
        return (
            {
                "ticker": sym,
                "source": "sec_edgar",
                "items": [],
                "error": "unknown_ticker",
                "note": "Ticker not found in SEC company_tickers mapping.",
            },
            calls,
        )

    cik_int = cmap[sym]
    cik_padded = str(cik_int).zfill(10)
    sub_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    time.sleep(max(0.0, float(settings.sec_request_delay_seconds)))
    calls += 1
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        r = client.get(sub_url, headers=_sec_headers())
        r.raise_for_status()
        sub = r.json()

    recent = (sub.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accs = recent.get("accessionNumber") or []
    prim = recent.get("primaryDocument") or []

    items: list[dict[str, Any]] = []
    want = max(1, min(int(limit), 8))
    for form, fdate, acc, doc in zip(forms, dates, accs, prim):
        if len(items) >= want:
            break
        if str(form) not in {"10-K", "10-Q", "8-K"}:
            continue
        if not acc or not doc:
            continue
        try:
            text, filing_sections = _fetch_filing_text_and_sections(cik_int, str(acc), str(doc))
            calls += 1
        except Exception as e:
            items.append(
                {
                    "form": str(form),
                    "published_at": str(fdate),
                    "accession": str(acc),
                    "primary_document": str(doc),
                    "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik_int)}/{_accession_to_nodash(str(acc))}/{doc}",
                    "source": "sec_edgar",
                    "error": "download_failed",
                    "detail": str(e)[:200],
                    "text": "",
                }
            )
            continue

        entry: dict[str, Any] = {
            "title": f"{form} filed {fdate}",
            "published_at": str(fdate),
            "form": str(form),
            "accession": str(acc),
            "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik_int)}/{_accession_to_nodash(str(acc))}/{doc}",
            "source": "sec_edgar",
            "text": text,
        }
        if filing_sections:
            entry["sections"] = filing_sections
        items.append(entry)

    bundle = {
        "ticker": sym,
        "source": "sec_edgar",
        "items": items,
        "cik": cik_int,
        "http_calls": calls,
    }
    return bundle, calls
