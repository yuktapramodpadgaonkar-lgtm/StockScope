"""
One-shot structured JSON narratives for Buy/Sell (education only).

Populates BuySellAiNarratives when generative backends are available.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import settings
from app.schemas.buy_sell_analysis import BuySellAiNarratives, BuySellReport
from services.ai.llm_service import LLMService
from services.ai.prompts import build_buy_sell_structured_narrative_json_prompt
from services.huggingface_inference_text import hf_generate_instruction_text

logger = logging.getLogger(__name__)
_llm = LLMService()

# Secondary structured narrative JSON pass must never block the HTTP request for minutes — cap Ollama waits
# even when buysell_llm_timeout_seconds is set very large in .env.
_STRUCTURED_NARRATIVE_OLLAMA_TIMEOUT_CAP_S = 90

_JSON_KEYS = (
    "thesis_expansion",
    "fundamentals_explained",
    "technical_explained",
    "sentiment_explained",
    "final_synthesis_ai",
    "risk_commentary_ai",
)


def strip_code_fences(text: str) -> str:
    t = text.strip()
    fence = re.match(r"^\s*```(?:json)?\s*\n(.*)\n```\s*$", t, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return t


def extract_first_json_object(text: str) -> dict[str, Any]:
    raw = strip_code_fences(text)
    start = raw.find("{")
    if start < 0:
        raise ValueError("no JSON object found")
    depth = 0
    end = -1
    for i in range(start, len(raw)):
        c = raw[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise ValueError("unbalanced JSON braces")
    return json.loads(raw[start:end])


def _report_context_blob(report: BuySellReport, bundle: dict[str, Any]) -> str:
    excluded = {"citations", "memory", "agent_pipeline", "ai_narratives"}
    core = report.model_dump(mode="json", exclude=excluded)
    lr = report.llm_review
    core["llm_review_compact"] = {
        "enabled": lr.enabled,
        "model": lr.model,
        "warnings": lr.warnings[:12],
        "rationale_preview": (lr.rationale or "")[:1600],
    }
    fld = ((bundle.get("fundamentals") or {}).get("fields") or {})
    ind = ((bundle.get("technical_indicators") or {}).get("indicators") or {})
    ns = bundle.get("news_and_sentiment") or {}
    keys_f = list(fld.keys())[:28]
    core["bundle_excerpt"] = {
        "fundamentals_fields": {str(k): fld[k] for k in keys_f},
        "technical_indicators_sample": dict(list(ind.items())[:22]),
        "news_primary_source": str(ns.get("primary_source") or ""),
    }
    blob = json.dumps(core, ensure_ascii=False, default=str)
    limit = 28_000
    if len(blob) > limit:
        blob = blob[:limit] + "…"
    return blob


def _narrative_backend_model(preferred_model: str) -> str | None:
    pref = (preferred_model or "hf_qwen").strip().lower()
    if pref == "finbert":
        if (settings.huggingface_api_token or "").strip():
            return "hf_qwen"
        return None
    if pref in {"hf_qwen", "hf_mistral_instruct", "gemini", "llama", "mistral"}:
        return pref
    return "hf_qwen"


def _invoke(prompt: str, backend: str) -> tuple[str, str]:
    b = backend.strip().lower()
    hf_map = {
        "hf_qwen": settings.hf_buy_sell_instruction_qwen_model_id.strip(),
        "hf_mistral_instruct": settings.hf_buy_sell_instruction_mistral_model_id.strip(),
    }
    if b in hf_map:
        mid = hf_map[b]
        if not mid or not (settings.huggingface_api_token or "").strip():
            raise RuntimeError("HF narrative model/token missing.")
        txt = hf_generate_instruction_text(
            prompt,
            model_id=mid,
            max_new_tokens=2048,
            temperature=0.2,
        )
        return txt.strip(), mid
    llm_pref = b if b in {"gemini", "llama", "mistral"} else "gemini"
    ollama_cap = min(
        max(15, int(settings.buysell_llm_timeout_seconds or 45)),
        _STRUCTURED_NARRATIVE_OLLAMA_TIMEOUT_CAP_S,
    )
    result = _llm.generate_response(
        prompt,
        preferred_model=llm_pref,
        ollama_timeout_seconds=ollama_cap,
        gemini_max_output_tokens=4096,
    )
    if result.error or not (result.response or "").strip():
        raise RuntimeError(result.error or "empty LLM response")
    model_label = result.model_used or llm_pref
    return result.response.strip(), model_label


def generate_buy_sell_ai_narratives(
    bundle: dict[str, Any],
    report: BuySellReport,
    *,
    preferred_model: str,
) -> BuySellAiNarratives | None:
    if not settings.buysell_llm_enabled:
        return None

    backend = _narrative_backend_model(preferred_model)
    if not backend:
        return None

    ctx = _report_context_blob(report, bundle)
    prompt = build_buy_sell_structured_narrative_json_prompt(ctx)

    last_err: str = ""
    tk = report.ticker.upper()
    for attempt in _try_backend_sequence(backend, preferred_model):
        try:
            raw_text, resolved = _invoke(prompt, attempt)
            data = extract_first_json_object(raw_text)
            out: dict[str, str] = {}
            for key in _JSON_KEYS:
                out[key] = str(data.get(key) or "").strip()
            if not any(out.values()):
                raise ValueError("all narrative fields empty")
            return BuySellAiNarratives(
                thesis_expansion=out["thesis_expansion"],
                fundamentals_explained=out["fundamentals_explained"],
                technical_explained=out["technical_explained"],
                sentiment_explained=out["sentiment_explained"],
                final_synthesis_ai=out["final_synthesis_ai"],
                risk_commentary_ai=out["risk_commentary_ai"],
                model_used=resolved,
            )
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)[:500]
            logger.warning("Buy/Sell structured narratives failed (%s backend %s): %s", tk, attempt, exc)

    logger.info("Giving up structured AI narratives for %s: %s", tk, last_err)
    return None


def _try_backend_sequence(primary: str, preferred_model: str) -> tuple[str, ...]:
    """
    Prefer HF + Gemini only unless the user explicitly picked an Ollama-backed model.
    Local Ollama can be slow or misconfigured; chaining it with a large env timeout was
    causing multi-minute requests and browser "Failed to fetch" timeouts.
    """
    pref = (preferred_model or "").strip().lower()
    tail: tuple[str, ...]
    if pref in {"llama", "mistral"}:
        tail = ("hf_qwen", "hf_mistral_instruct", "gemini", "llama", "mistral")
    else:
        tail = ("hf_qwen", "hf_mistral_instruct", "gemini")
    ordered: list[str] = []
    seen: set[str] = set()
    for cand in (primary, *tail):
        if cand in seen:
            continue
        seen.add(cand)
        ordered.append(cand)
    return tuple(ordered)
