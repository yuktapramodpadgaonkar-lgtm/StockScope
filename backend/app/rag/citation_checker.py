from __future__ import annotations

from typing import Any


def verify_citation_ids(citation_ids: list[str], retrieved: list[dict[str, Any]]) -> dict[str, Any]:
    available = {str(r.get("chunk_id") or "") for r in retrieved}
    used = [c for c in citation_ids if c in available]
    missing = [c for c in citation_ids if c and c not in available]
    return {
        "used_count": len(used),
        "missing_count": len(missing),
        "missing_ids": missing,
    }

