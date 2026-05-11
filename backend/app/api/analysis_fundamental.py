from __future__ import annotations

import json
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.rag import ingest_filings_chunks, retrieve_chunks
from app.rag.embedding_index import sync_embeddings_for_ticker
from app.rag.store import load_chunks
from app.schemas.fundamental import FundamentalAnalysisResponse, RagEvidenceItem
from app.services.ai.fundamental_prompt import (
    build_fundamental_prompt,
    build_fundamental_rag_prompt,
    build_fundamental_rag_repair_prompt,
    build_fundamental_repair_prompt,
)
from app.tools.filings_tool import get_filings_or_transcripts
from app.services.auth_service import verify_access_token
from app.services.fundamental_service import get_fundamental_report
from services.ai.llm_service import LLMService

router = APIRouter(prefix="/api/analysis/fundamental", tags=["Fundamental Analysis"])

LLM_UNAVAILABLE = "AI summary unavailable. Deterministic analysis is still provided."
_bearer = HTTPBearer(auto_error=False)
_llm = LLMService()
_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")


def _ai_error_message(llm_detail: str | None) -> str:
    detail = (llm_detail or "").strip()
    if not detail:
        return LLM_UNAVAILABLE
    cap = 320
    if len(detail) > cap:
        detail = detail[: cap - 1] + "…"
    return f"{LLM_UNAVAILABLE} ({detail})"


def _significant_numbers(text: str) -> list[str]:
    out: list[str] = []
    for m in _NUM_RE.finditer(text or ""):
        s = m.group(0)
        if "." in s:
            out.append(s)
            continue
        try:
            n = int(s)
        except ValueError:
            continue
        # ignore likely years and tiny integers
        if 1990 <= n <= 2035:
            continue
        if n < 10:
            continue
        out.append(s)
    return out


def _fundamental_summary_needs_repair(
    summary: str, report: dict, evidence_text: str | None = None
) -> bool:
    corpus = json.dumps(report, ensure_ascii=False)
    if evidence_text:
        corpus = f"{corpus}\n{evidence_text}"
    for num in _significant_numbers(summary):
        if num not in corpus:
            return True
    return False


def _format_filing_evidence_block(rows: list[dict]) -> str:
    lines: list[str] = []
    for r in rows:
        title = str(r.get("title") or "").strip() or "(filing)"
        url = str(r.get("url") or "").strip()
        sk = str(r.get("section_key") or "").strip()
        head = f"{title}" + (f" [{sk}]" if sk else "")
        excerpt = str(r.get("text") or "").strip().replace("\n", " ")[:1200]
        lines.append(f"- {head} | {url or 'n/a'} | {excerpt}")
    return "\n".join(lines) if lines else ""


def _rows_to_rag_evidence(rows: list[dict]) -> list[RagEvidenceItem]:
    out: list[RagEvidenceItem] = []
    for r in rows:
        text = str(r.get("text") or "").strip()
        preview = text[:480] + ("…" if len(text) > 480 else "")
        out.append(
            RagEvidenceItem(
                chunk_id=str(r.get("chunk_id") or "") or None,
                title=str(r.get("title") or "") or None,
                url=str(r.get("url") or "") or None,
                section_key=str(r.get("section_key") or "") or None,
                text_preview=preview or "(empty)",
                retrieval_score=(
                    float(r["retrieval_score"])
                    if r.get("retrieval_score") is not None
                    else None
                ),
            )
        )
    return out


def _run_filing_rag(sym: str, *, top_k: int = 8) -> tuple[list[dict], str | None]:
    try:
        filings = get_filings_or_transcripts(sym)
        bundle = {"filings_or_transcripts": filings}
        ingest_filings_chunks(sym, bundle)
        ticker_rows = [
            c
            for c in load_chunks()
            if str(c.get("ticker") or "").upper() == sym
        ]
        sync_embeddings_for_ticker(sym, ticker_rows)
        q = (
            f"risk factors business outlook MD&A liquidity results operations "
            f"competition regulation for {sym}"
        )
        retrieved = retrieve_chunks(
            ticker=sym,
            query=q,
            top_k=top_k,
            doc_types=["filing"],
            max_age_days=None,
        )
        return retrieved, None
    except Exception as e:  # noqa: BLE001
        return [], str(e)[:500]


def _require_bearer_email(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = verify_access_token(creds.credentials)
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return email


@router.get("", response_model=FundamentalAnalysisResponse)
def get_fundamental_analysis(
    ticker: str = Query(..., min_length=1, max_length=32, description="Stock symbol, e.g. AAPL"),
    include_llm: bool = Query(
        False,
        description="If true, request an optional AI explanation (best-effort).",
    ),
    preferred_model: str = Query(
        "llama",
        description="Preferred LLM: gemini | llama | mistral (auto-fallback applies).",
    ),
    include_rag: bool = Query(
        False,
        description="If true, ingest recent SEC filing chunks, hybrid-retrieve excerpts, and return rag_evidence (and ground the LLM when include_llm is true).",
    ),
    _email: str = Depends(_require_bearer_email),
) -> FundamentalAnalysisResponse:
    try:
        data = get_fundamental_report(ticker)
    except ValueError as e:
        msg = str(e)
        if "required" in msg.lower():
            raise HTTPException(status_code=400, detail=msg) from e
        raise HTTPException(status_code=404, detail=msg) from e

    ai_summary: str | None = None
    ai_model: str | None = None
    ai_error: str | None = None
    rag_evidence: list[RagEvidenceItem] | None = None
    rag_error: str | None = None
    evidence_block = ""

    sym_u = ticker.strip().upper()
    if include_rag:
        filing_rows, rag_err = _run_filing_rag(sym_u)
        rag_error = rag_err
        rag_evidence = _rows_to_rag_evidence(filing_rows)
        if filing_rows:
            evidence_block = _format_filing_evidence_block(filing_rows)

    if include_llm:
        use_rag_prompt = bool(include_rag and evidence_block.strip())
        prompt = (
            build_fundamental_rag_prompt(data, evidence_block)
            if use_rag_prompt
            else build_fundamental_prompt(data)
        )
        llm_result = _llm.generate_response(prompt, preferred_model=preferred_model)
        if llm_result.error or not llm_result.response:
            ai_error = _ai_error_message(llm_result.error)
        else:
            ai_summary = llm_result.response
            ai_model = llm_result.model_used
            if isinstance(ai_summary, str) and ai_summary.strip() and _fundamental_summary_needs_repair(
                ai_summary, data, evidence_block if use_rag_prompt else None
            ):
                repair_prompt = (
                    build_fundamental_rag_repair_prompt(
                        report=data,
                        evidence_block=evidence_block,
                        previous_text=ai_summary,
                        problem="numeric_claim_not_in_deterministic_report_or_evidence",
                    )
                    if use_rag_prompt
                    else build_fundamental_repair_prompt(
                        report=data,
                        previous_text=ai_summary,
                        problem="numeric_claim_not_in_deterministic_report",
                    )
                )
                repair_result = _llm.generate_response(repair_prompt, preferred_model=preferred_model)
                if not repair_result.error and repair_result.response:
                    ai_summary = repair_result.response.strip()
                    ai_model = repair_result.model_used
                else:
                    ai_error = _ai_error_message(
                        "AI summary contained unsupported numeric claims; repair failed"
                    )

    payload = {
        **data,
        "ai_summary": ai_summary,
        "ai_model": ai_model,
        "ai_error": ai_error,
        "rag_evidence": rag_evidence,
        "rag_error": rag_error,
    }
    return FundamentalAnalysisResponse.model_validate(payload)
