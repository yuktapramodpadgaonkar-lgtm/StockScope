from __future__ import annotations

import json
from pathlib import Path


def test_eval_set_has_minimum_cases_and_required_fields() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "backend" / "evaluation" / "eval_set.json"
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    assert isinstance(data, list)
    assert len(data) >= 50

    required = {"id", "category", "input", "expected_behavior", "checks"}
    for row in data:
        assert isinstance(row, dict)
        missing = required - set(row.keys())
        assert not missing, f"missing keys {sorted(missing)} for case {row.get('id')!r}"
        assert isinstance(row.get("id"), str) and row["id"].strip()
        assert isinstance(row.get("category"), str) and row["category"].strip()
        assert isinstance(row.get("input"), dict)
        assert isinstance(row.get("expected_behavior"), str) and row["expected_behavior"].strip()
        assert isinstance(row.get("checks"), list)

