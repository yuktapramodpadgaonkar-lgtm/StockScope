"""Append-only JSONL logs for model and tool calls (course / rubric observability)."""

from __future__ import annotations

import json
import time
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_LOG_DIR = _BACKEND_ROOT / "logs"
_PREVIEW = 240


def _append_line(filename: str, record: dict) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    record.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    path = _LOG_DIR / filename
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _preview_text(text: str | None) -> tuple[str | None, int | None]:
    if text is None:
        return None, None
    s = text if isinstance(text, str) else str(text)
    ln = len(s)
    if ln <= _PREVIEW:
        return s, ln
    return s[:_PREVIEW] + "…", ln


def log_model_call(
    *,
    provider: str,
    model: str,
    task: str,
    prompt: str | None = None,
    output: str | None = None,
    latency_ms: float | int | None = None,
    error: str | None = None,
) -> None:
    pp, plen = _preview_text(prompt)
    op, olen = _preview_text(output)
    _append_line(
        "model_calls.jsonl",
        {
            "provider": provider,
            "model": model,
            "task": task,
            "prompt_preview": pp,
            "prompt_length": plen,
            "output_preview": op,
            "output_length": olen,
            "latency_ms": latency_ms,
            "error": error,
        },
    )


def log_tool_call(
    *,
    tool_name: str,
    input_summary: str,
    output_summary: str,
    latency_ms: float | int | None = None,
    error: str | None = None,
) -> None:
    _append_line(
        "tool_calls.jsonl",
        {
            "tool_name": tool_name,
            "input_summary": (input_summary or "")[:500],
            "output_summary": (output_summary or "")[:500],
            "latency_ms": latency_ms,
            "error": error,
        },
    )
