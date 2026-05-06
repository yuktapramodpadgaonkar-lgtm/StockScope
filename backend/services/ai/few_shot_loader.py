"""Load per-feature few-shot exemplars from backend/evaluation/few_shot/*.json."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_FEW_SHOT_DIR = _BACKEND_ROOT / "evaluation" / "few_shot"

_HEADER = (
    "Few-shot examples (match format, tone, and safety rules; "
    "do not copy any example facts into your answer — use only real context below):"
)


def _render_shot(shot: dict[str, Any], index: int) -> list[str]:
    label = str(shot.get("label") or f"Example {index}")
    lines = [f"\n### {label}"]
    if "text" in shot and shot["text"]:
        lines.append(str(shot["text"]).strip())
    if "report_excerpt" in shot:
        lines.append(json.dumps(shot["report_excerpt"], indent=2, ensure_ascii=False))
    if "headlines_sample" in shot:
        lines.append("Sample headlines block:")
        lines.append(str(shot["headlines_sample"]).strip())
    if "output_json" in shot:
        lines.append("Good JSON shape:")
        lines.append(json.dumps(shot["output_json"], indent=2, ensure_ascii=False))
    if "input_report" in shot:
        lines.append("Snapshot JSON (illustrative):")
        lines.append(json.dumps(shot["input_report"], indent=2, ensure_ascii=False)[:2500])
    if "assistant" in shot:
        lines.append("Good assistant reply:")
        lines.append(str(shot["assistant"]).strip())
    if "json_output" in shot:
        lines.append("Good JSON output:")
        lines.append(json.dumps(shot["json_output"], indent=2, ensure_ascii=False))
    return lines


@lru_cache(maxsize=32)
def _raw_feature_file(stem: str) -> str:
    path = _FEW_SHOT_DIR / f"{stem}.json"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def few_shot_examples_block(
    feature: str,
    *,
    variant: str | None = None,
    max_items: int = 2,
) -> str:
    """
    feature: stem of few_shot/<feature>.json (e.g. buy_sell, news_themes).
    variant: if JSON has top-level \"variants\", select variants[variant].shots.
    """
    raw = _raw_feature_file(feature)
    if not raw.strip():
        return ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ""

    shots: list[Any]
    if variant and isinstance(data.get("variants"), dict):
        bucket = data["variants"].get(variant) or {}
        shots = list(bucket.get("shots") or [])
    else:
        shots = list(data.get("shots") or [])

    if not shots:
        return ""

    lines = [_HEADER]
    for i, shot in enumerate(shots[:max_items], 1):
        if not isinstance(shot, dict):
            continue
        lines.extend(_render_shot(shot, i))
    return "\n".join(lines).strip()
