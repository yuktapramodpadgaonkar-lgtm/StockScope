#!/usr/bin/env python3
"""
Trade-off scatter: x = latency (s), y = judge score (1–5), one point per model.

Reads overall rows from metrics_<stamp>.csv (same run as feature multimodel eval).

From repo root:
  python backend/evaluation/plot_latency_judge_tradeoff.py --stamp 20260510-182232
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

MODELS = ("gemini", "llama", "mistral")
LABELS = ("Gemini", "LLaMA", "Mistral")
COLORS = ("#1a73e8", "#7c3aed", "#ea580c")


def _load_overall(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        if r.get("scope") == "overall" and r.get("task") == "all":
            m = (r.get("model") or "").strip().lower()
            if m:
                out[m] = r
    return out


def _f(row: dict[str, str], key: str) -> float | None:
    v = (row.get(key) or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Latency vs judge score trade-off (one point per model)")
    parser.add_argument("--stamp", default="", help="Use results/metrics_<stamp>.csv")
    parser.add_argument("--csv", default="", help="Explicit metrics CSV path")
    parser.add_argument("--out", default="", help="Output PNG path")
    parser.add_argument("--results-dir", default=str(Path(__file__).resolve().parent / "results"))
    args = parser.parse_args()

    if args.csv:
        csv_path = Path(args.csv)
        stamp = csv_path.stem.replace("metrics_", "") or "run"
    elif args.stamp:
        stamp = args.stamp
        csv_path = Path(args.results_dir) / f"metrics_{stamp}.csv"
    else:
        raise SystemExit("Provide --stamp or --csv")

    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    by_m = _load_overall(csv_path)
    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise SystemExit("matplotlib required: pip install matplotlib") from e

    xs: list[float] = []
    ys: list[float] = []
    for m in MODELS:
        row = by_m.get(m) or {}
        lx = _f(row, "avg_latency_s")
        jy = _f(row, "judge_overall")
        if lx is None or jy is None:
            raise SystemExit(f"Missing latency or judge_overall for model {m}")
        xs.append(lx)
        ys.append(jy)

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor("#fafafa")
    ax.set_facecolor("#fafafa")

    for i, m in enumerate(MODELS):
        ax.scatter(
            [xs[i]],
            [ys[i]],
            s=420,
            c=COLORS[i],
            edgecolors="white",
            linewidths=2.5,
            zorder=5,
        )
        offsets_pt = ((22, 28), (22, -42), (-95, 18))
        ox, oy = offsets_pt[i]
        ax.annotate(
            f"{LABELS[i]}\n{ys[i]:.2f} @ {xs[i]:.1f}s",
            (xs[i], ys[i]),
            textcoords="offset points",
            xytext=(ox, oy),
            fontsize=11,
            fontweight="medium",
            ha="left" if i != 2 else "right",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#ddd", alpha=0.95),
            zorder=6,
        )

    ax.set_xlabel("Mean latency (seconds)", fontsize=12, fontweight="semibold")
    ax.set_ylabel("Mean judge score (1–5)", fontsize=12, fontweight="semibold")
    ax.set_title("Latency vs. quality trade-off\n(lower-left = faster & lower judge; upper-right = slower & higher judge)", fontsize=13, pad=14)
    ax.set_xlim(left=max(0, min(xs) - 2), right=max(xs) + 2)
    ax.set_ylim(1.0, 5.2)
    ax.grid(True, alpha=0.35, linestyle="-", linewidth=0.8)
    ax.axhline(5.0, color="#bbb", linestyle="--", linewidth=0.9, zorder=0)

    # Ideal quadrant hint (subtle)
    ax.text(
        0.02,
        0.98,
        "↑ higher judge\n← lower latency",
        transform=ax.transAxes,
        fontsize=9,
        color="#666",
        va="top",
        ha="left",
    )

    fig.tight_layout()
    out = Path(args.out) if args.out else Path(args.results_dir) / f"latency_judge_tradeoff_{stamp}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
