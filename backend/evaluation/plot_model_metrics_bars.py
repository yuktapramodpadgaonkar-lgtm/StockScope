#!/usr/bin/env python3
"""
Bar charts: Gemini vs LLaMA vs Mistral from metrics_<stamp>.csv (overall rows).

Metrics: latency (s), grounding (0–1), completeness (0–1), hallucination rate (%).

From repo root:
  python backend/evaluation/plot_model_metrics_bars.py --stamp 20260510-182232
  python backend/evaluation/plot_model_metrics_bars.py --csv path/to/metrics.csv --out chart.png
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


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


def _f(row: dict[str, str], key: str, default: float = 0.0) -> float:
    v = (row.get(key) or "").strip()
    if not v:
        return default
    try:
        return float(v)
    except ValueError:
        return default


def main() -> int:
    parser = argparse.ArgumentParser(description="Bar chart: Gemini / LLaMA / Mistral model metrics")
    parser.add_argument("--stamp", default="", help="Use backend/evaluation/results/metrics_<stamp>.csv")
    parser.add_argument("--csv", default="", help="Explicit path to metrics CSV")
    parser.add_argument(
        "--out",
        default="",
        help="Output PNG path (default: results/model_metrics_bars_<stamp>.png)",
    )
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

    by_model = _load_overall(csv_path)
    order = ("gemini", "llama", "mistral")
    display = ("Gemini", "LLaMA", "Mistral")
    colors = ("#1a73e8", "#7c3aed", "#ea580c")

    missing = [m for m in order if m not in by_model]
    if missing:
        raise SystemExit(f"Missing overall rows for models: {missing}")

    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise SystemExit(
            "matplotlib is required. Install with: pip install matplotlib"
        ) from e

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    fig.suptitle("Multi-model comparison (overall)", fontsize=14, fontweight="bold")

    panels = [
        (axes[0, 0], "avg_latency_s", "Latency (seconds)", "lower is better"),
        (axes[0, 1], "avg_grounding_score", "Grounding (0–1)", "higher is better"),
        (axes[1, 0], "avg_completeness_score", "Completeness (0–1)", "higher is better"),
        (axes[1, 1], "hallucination_rate_pct", "Hallucination rate (%)", "lower is better"),
    ]

    x = range(len(order))
    for ax, col, title, subtitle in panels:
        vals = [_f(by_model[m], col) for m in order]
        bars = ax.bar(x, vals, color=colors, edgecolor="white", linewidth=1.2)
        ax.set_xticks(list(x))
        ax.set_xticklabels(display)
        ax.set_title(title)
        ax.set_ylabel(subtitle, fontsize=9, style="italic", color="#555")
        ymax = max(vals) * 1.15 if max(vals) > 0 else 1.0
        ax.set_ylim(0, ymax)
        for b, v in zip(bars, vals):
            ax.text(
                b.get_x() + b.get_width() / 2,
                b.get_height() + ymax * 0.02,
                f"{v:.2f}" if col != "hallucination_rate_pct" else f"{v:.0f}%",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    fig.tight_layout()
    out = Path(args.out) if args.out else Path(args.results_dir) / f"model_metrics_bars_{stamp}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
