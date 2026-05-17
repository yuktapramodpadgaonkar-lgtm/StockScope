#!/usr/bin/env python3
"""
Grouped bar chart: x = tasks (buy_sell, chat, fundamental, sentiment),
y = judge_score (mean 1–5 from metrics CSV), grouped by model.

CSV `task` values from feature multimodel eval map to x-axis labels:
  agentic_rag -> chat, news_sentiment -> sentiment; buy_sell and fundamental unchanged.

From repo root:
  python backend/evaluation/plot_judge_score_grouped.py --stamp 20260510-182232
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

# x-axis order and display labels (must match user request)
X_TASKS = ("buy_sell", "chat", "fundamental", "sentiment")

# CSV `task` column -> x-axis key
CSV_TASK_TO_X = {
    "buy_sell": "buy_sell",
    "agentic_rag": "chat",
    "fundamental": "fundamental",
    "news_sentiment": "sentiment",
}

MODELS = ("gemini", "llama", "mistral")
MODEL_LABELS = ("Gemini", "LLaMA", "Mistral")
COLORS = ("#1a73e8", "#7c3aed", "#ea580c")


def _parse_judge(row: dict[str, str]) -> float | None:
    v = (row.get("judge_overall") or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _load_task_judge_scores(csv_path: Path) -> dict[str, dict[str, float | None]]:
    """model -> x_task -> score"""
    out: dict[str, dict[str, float | None]] = {m: {t: None for t in X_TASKS} for m in MODELS}
    with csv_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("scope") != "task":
                continue
            raw_task = (row.get("task") or "").strip()
            x_key = CSV_TASK_TO_X.get(raw_task)
            if x_key is None:
                continue
            model = (row.get("model") or "").strip().lower()
            if model not in out:
                continue
            out[model][x_key] = _parse_judge(row)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Grouped bar chart: judge score by task and model")
    parser.add_argument("--stamp", default="", help="Use results/metrics_<stamp>.csv")
    parser.add_argument("--csv", default="", help="Explicit metrics CSV path")
    parser.add_argument("--out", default="", help="Output PNG (default: results/judge_score_grouped_<stamp>.png)")
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

    scores = _load_task_judge_scores(csv_path)

    try:
        import matplotlib.pyplot as plt
    except ImportError as e:
        raise SystemExit("Need matplotlib. pip install matplotlib") from e

    n_tasks = len(X_TASKS)
    n_models = len(MODELS)
    x_idx = [float(j) for j in range(n_tasks)]
    bar_w = 0.22
    half = (n_models - 1) / 2.0
    offsets = [(i - half) * bar_w for i in range(n_models)]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for mi, model in enumerate(MODELS):
        ys: list[float] = []
        for xk in X_TASKS:
            v = scores[model].get(xk)
            ys.append(float(v) if v is not None else 0.0)
        pos = [x_idx[j] + offsets[mi] for j in range(n_tasks)]
        bars = ax.bar(
            pos,
            ys,
            bar_w,
            label=MODEL_LABELS[mi],
            color=COLORS[mi],
            edgecolor="white",
            linewidth=1.0,
        )
        for b, y in zip(bars, ys):
            if y > 0:
                ax.text(
                    b.get_x() + b.get_width() / 2,
                    b.get_height() + 0.05,
                    f"{y:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    ax.set_xticks(x_idx)
    ax.set_xticklabels(list(X_TASKS))
    ax.set_xlabel("Task")
    ax.set_ylabel("Judge score (1–5, mean)")
    ax.set_title("LLM-as-judge mean score by task and model")
    ax.set_ylim(0, 5.5)
    ax.axhline(5.0, color="#ccc", linestyle="--", linewidth=0.8, zorder=0)
    ax.legend(title="Model", loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    out = (
        Path(args.out)
        if args.out
        else Path(args.results_dir) / f"judge_score_grouped_{stamp}.png"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
