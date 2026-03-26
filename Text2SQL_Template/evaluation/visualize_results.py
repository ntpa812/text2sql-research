"""
Evaluation Results Visualizer
Generates charts from pipeline evaluation results.

Usage:
    python evaluation/visualize_results.py [--result evaluation/results/YYYY-MM-DD_HH-MM-SS.json]
    python evaluation/visualize_results.py  # auto-picks latest result
"""

import argparse
import json
import os
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _PROJECT_ROOT)

import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams["font.family"] = ["DejaVu Sans", "sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

import numpy as np


def load_result(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_latest_result() -> str:
    results_dir = os.path.join(_PROJECT_ROOT, "evaluation", "results")
    files = sorted(Path(results_dir).glob("*.json"))
    if not files:
        print("ERROR: No result files found in evaluation/results/")
        sys.exit(1)
    return str(files[-1])


# ============================================================
# Chart 1: Component Accuracy Overview (horizontal bar)
# ============================================================
def chart_component_accuracy(data: dict, output_dir: str):
    metrics = data["metrics"]

    components = ["Domain Routing", "Table Selection", "Intent Detection",
                  "Entity F1", "SQL Contains", "Validator"]
    values = [
        metrics["domain_routing"]["accuracy"],
        metrics["table_selection"]["accuracy"],
        metrics["intent_detection"]["accuracy"],
        metrics["entity_extraction"]["f1"],
        metrics["sql_contains"]["accuracy"],
        metrics["validator"]["accuracy"],
    ]

    # CI bars where available
    ci_lo = []
    ci_hi = []
    for comp_key, comp_name in [
        ("domain_routing", "Domain Routing"),
        ("table_selection", "Table Selection"),
        ("intent_detection", "Intent Detection"),
        (None, "Entity F1"),
        ("sql_contains", "SQL Contains"),
        ("validator", "Validator"),
    ]:
        if comp_key and "ci_95" in metrics.get(comp_key, {}):
            ci = metrics[comp_key]["ci_95"]
            ci_lo.append(ci[0])
            ci_hi.append(ci[1])
        else:
            ci_lo.append(None)
            ci_hi.append(None)

    fig, ax = plt.subplots(figsize=(10, 5))

    colors = []
    for v in values:
        if v >= 90:
            colors.append("#2ecc71")
        elif v >= 70:
            colors.append("#f39c12")
        elif v >= 50:
            colors.append("#e67e22")
        else:
            colors.append("#e74c3c")

    y_pos = np.arange(len(components))
    bars = ax.barh(y_pos, values, color=colors, height=0.6, edgecolor="white", linewidth=0.5)

    # CI whiskers
    for i, (lo, hi) in enumerate(zip(ci_lo, ci_hi)):
        if lo is not None and hi is not None:
            ax.plot([lo, hi], [i, i], color="#333", linewidth=2, marker="|", markersize=8)

    # Value labels
    for i, (bar, v) in enumerate(zip(bars, values)):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}%", va="center", fontsize=11, fontweight="bold")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(components, fontsize=11)
    ax.set_xlim(0, 110)
    ax.set_xlabel("Accuracy (%)", fontsize=11)
    ax.set_title("Pipeline Component Accuracy", fontsize=14, fontweight="bold")
    ax.invert_yaxis()

    # Reference lines
    ax.axvline(x=90, color="#2ecc71", linestyle="--", alpha=0.3, label="90% (good)")
    ax.axvline(x=70, color="#f39c12", linestyle="--", alpha=0.3, label="70% (fair)")
    ax.legend(loc="lower right", fontsize=9)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = os.path.join(output_dir, "component_accuracy.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ============================================================
# Chart 2: Entity Extraction Per-Type F1 (bar chart)
# ============================================================
def chart_entity_per_type(data: dict, output_dir: str):
    per_type = data["metrics"]["entity_extraction"]["per_type"]
    if not per_type:
        return

    # Sort by F1 descending
    sorted_types = sorted(per_type.items(), key=lambda x: x[1]["f1"], reverse=True)
    names = [t[0] for t in sorted_types]
    f1_vals = [t[1]["f1"] * 100 for t in sorted_types]
    p_vals = [t[1]["precision"] * 100 for t in sorted_types]
    r_vals = [t[1]["recall"] * 100 for t in sorted_types]
    supports = [t[1]["support"] for t in sorted_types]

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(names))
    width = 0.25

    bars_p = ax.bar(x - width, p_vals, width, label="Precision", color="#3498db", alpha=0.85)
    bars_r = ax.bar(x, r_vals, width, label="Recall", color="#e74c3c", alpha=0.85)
    bars_f = ax.bar(x + width, f1_vals, width, label="F1", color="#2ecc71", alpha=0.85)

    # Support annotation
    for i, s in enumerate(supports):
        ax.text(i + width, f1_vals[i] + 2, f"n={s}", ha="center", fontsize=8, color="#666")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Score (%)", fontsize=11)
    ax.set_ylim(0, 115)
    ax.set_title("Entity Extraction: Per-Type P/R/F1", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.axhline(y=80, color="#999", linestyle="--", alpha=0.3)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = os.path.join(output_dir, "entity_per_type.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ============================================================
# Chart 3: Per-Question Heatmap
# ============================================================
def chart_per_question_heatmap(data: dict, output_dir: str):
    details = data["details"]
    components = ["domain", "tables", "intent", "entities", "sql", "validator"]
    comp_labels = ["Domain", "Tables", "Intent", "Entities", "SQL", "Validator"]

    n = len(details)
    matrix = np.zeros((n, len(components)))

    q_labels = []
    for i, d in enumerate(details):
        qid = d.get("id", f"Q{i+1}")
        q_labels.append(qid)
        for j, comp in enumerate(components):
            if comp == "entities":
                # Use F1 score (0-1)
                matrix[i][j] = d.get("entities", {}).get("f1", 0.0)
            elif comp == "sql":
                matrix[i][j] = 1.0 if d.get("sql", {}).get("contains_pass", False) else 0.0
            else:
                matrix[i][j] = 1.0 if d.get(comp, {}).get("pass", False) else 0.0

    fig, ax = plt.subplots(figsize=(8, max(8, n * 0.35)))

    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("rg", ["#e74c3c", "#f39c12", "#2ecc71"])
    im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(np.arange(len(comp_labels)))
    ax.set_xticklabels(comp_labels, fontsize=10, rotation=30, ha="right")
    ax.set_yticks(np.arange(n))
    ax.set_yticklabels(q_labels, fontsize=8)

    # Annotate cells
    for i in range(n):
        for j in range(len(components)):
            val = matrix[i][j]
            text = "P" if val >= 1.0 else (f"{val:.0%}" if val > 0 else "F")
            color = "white" if val < 0.5 else "black"
            ax.text(j, i, text, ha="center", va="center", fontsize=7, color=color, fontweight="bold")

    ax.set_title("Per-Question Component Results", fontsize=14, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax, shrink=0.6)
    cbar.set_label("Score", fontsize=10)

    plt.tight_layout()
    path = os.path.join(output_dir, "per_question_heatmap.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ============================================================
# Chart 4: Error Distribution (pie / donut)
# ============================================================
def chart_error_distribution(data: dict, output_dir: str):
    ea = data["error_analysis"]
    components = ["domain", "tables", "intent", "entities", "sql", "validator"]
    labels = []
    sizes = []
    for comp in components:
        count = ea.get(comp, {}).get("count", 0)
        if count > 0:
            labels.append(comp.capitalize())
            sizes.append(count)

    if not sizes:
        return

    fig, ax = plt.subplots(figsize=(7, 7))

    colors = ["#e74c3c", "#e67e22", "#f39c12", "#3498db", "#9b59b6", "#1abc9c"]
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%", startangle=90,
        colors=colors[:len(sizes)], pctdistance=0.75,
        wedgeprops={"linewidth": 2, "edgecolor": "white"},
    )

    for t in autotexts:
        t.set_fontsize(11)
        t.set_fontweight("bold")

    # Donut
    centre_circle = plt.Circle((0, 0), 0.45, fc="white")
    ax.add_artist(centre_circle)

    total_errors = sum(sizes)
    ax.text(0, 0, f"{total_errors}\nerrors", ha="center", va="center", fontsize=16, fontweight="bold")

    ax.set_title("Error Distribution by Component", fontsize=14, fontweight="bold")

    plt.tight_layout()
    path = os.path.join(output_dir, "error_distribution.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ============================================================
# Chart 5: Difficulty breakdown
# ============================================================
def chart_difficulty_breakdown(data: dict, output_dir: str):
    details = data["details"]

    diff_stats = {}
    for d in details:
        diff = d.get("difficulty", "unknown")
        if diff not in diff_stats:
            diff_stats[diff] = {"total": 0, "pass": 0}
        diff_stats[diff]["total"] += 1
        # "all pass" = all components pass
        all_pass = (
            d.get("domain", {}).get("pass", False)
            and d.get("tables", {}).get("pass", False)
            and d.get("intent", {}).get("pass", False)
            and d.get("entities", {}).get("f1", 0) >= 1.0
            and d.get("sql", {}).get("contains_pass", False)
        )
        if all_pass:
            diff_stats[diff]["pass"] += 1

    order = ["easy", "medium", "hard"]
    labels = [d for d in order if d in diff_stats]
    totals = [diff_stats[d]["total"] for d in labels]
    passes = [diff_stats[d]["pass"] for d in labels]
    fails = [t - p for t, p in zip(totals, passes)]

    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(len(labels))
    width = 0.4

    ax.bar(x, passes, width, label="All Pass", color="#2ecc71")
    ax.bar(x, fails, width, bottom=passes, label="Has Failures", color="#e74c3c")

    for i in range(len(labels)):
        rate = passes[i] / totals[i] * 100 if totals[i] else 0
        ax.text(i, totals[i] + 0.2, f"{rate:.0f}%", ha="center", fontsize=11, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([d.capitalize() for d in labels], fontsize=12)
    ax.set_ylabel("Number of Questions", fontsize=11)
    ax.set_title("Pass Rate by Difficulty", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = os.path.join(output_dir, "difficulty_breakdown.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Visualize pipeline evaluation results")
    parser.add_argument("--result", help="Path to result JSON (default: latest)")
    parser.add_argument("--output", help="Output directory for charts (default: evaluation/charts/)")
    args = parser.parse_args()

    result_path = args.result or find_latest_result()
    print(f"Loading: {result_path}")
    data = load_result(result_path)

    output_dir = args.output or os.path.join(_PROJECT_ROOT, "evaluation", "charts")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Generating charts in: {output_dir}\n")

    chart_component_accuracy(data, output_dir)
    chart_entity_per_type(data, output_dir)
    chart_per_question_heatmap(data, output_dir)
    chart_error_distribution(data, output_dir)
    chart_difficulty_breakdown(data, output_dir)

    print(f"\nDone! {5} charts saved to {output_dir}")


if __name__ == "__main__":
    main()
