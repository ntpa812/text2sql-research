"""
Pipeline Evaluation Script
Runs gold test set through pipeline and computes per-component accuracy metrics.

Usage:
    python evaluation/evaluate_pipeline.py
    python evaluation/evaluate_pipeline.py --gold data/evaluation/gold_test_set.jsonl
    python evaluation/evaluate_pipeline.py --no-explain
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Setup path and env before any project imports
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import numpy as np

from pipeline.runner import run_pipeline

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================
# Gold test set loader
# ============================================================

def load_gold_set(path: str) -> List[Dict[str, Any]]:
    """Load JSONL gold test set (one JSON object per line)."""
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  WARNING: Skipping line {line_no}: {e}")
    return entries


# ============================================================
# Component evaluators
# ============================================================

def eval_domain(gold: Dict, result: Dict) -> bool:
    """Domain routing: exact match."""
    return gold.get("domain") == result.get("domain")


def eval_tables(gold: Dict, result: Dict) -> bool:
    """Table selection: gold tables subset of predicted tables."""
    gold_tables = set(gold.get("tables", []))
    pred_tables = set(result.get("tables", []))
    if not gold_tables:
        return True
    return gold_tables.issubset(pred_tables)


def eval_intent(gold: Dict, result: Dict) -> bool:
    """Intent detection: exact match on intent ID."""
    return gold.get("intent") == result.get("intent")


def eval_entities(gold: Dict, result: Dict) -> Dict[str, Any]:
    """
    Entity extraction: precision, recall, F1.
    TP = key present in both AND values match (normalized).
    """
    gold_ents = gold.get("entities", {})
    pred_ents = result.get("entities", {})

    if not gold_ents and not pred_ents:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0, "details": {}}

    tp = 0
    fp = 0
    fn = 0
    details = {}

    for key, gold_val in gold_ents.items():
        pred_val = pred_ents.get(key)
        if pred_val is not None and _normalize_entity_value(pred_val) == _normalize_entity_value(gold_val):
            tp += 1
            details[key] = "TP"
        else:
            fn += 1
            details[key] = f"FN (pred={pred_val})"

    for key in pred_ents:
        if key not in gold_ents:
            fp += 1
            details[key] = f"FP (pred={pred_ents[key]})"

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "details": details}


def _normalize_entity_value(val: str) -> str:
    """Normalize entity value for comparison."""
    val = str(val).strip()
    # Keep numeric/date values as-is for exact comparison
    if val.replace("-", "").replace(".", "").isdigit():
        return val
    return val.lower()


def eval_sql_contains(gold: Dict, result: Dict) -> Dict[str, Any]:
    """Check if predicted SQL contains all required fragments."""
    fragments = gold.get("sql_contains", [])
    sql = (result.get("sql") or "").lower()

    if not fragments:
        return {"pass": True, "matched": 0, "total": 0, "missing": []}

    missing = [f for f in fragments if f.lower() not in sql]
    matched = len(fragments) - len(missing)

    return {
        "pass": len(missing) == 0,
        "matched": matched,
        "total": len(fragments),
        "missing": missing,
    }


def eval_validator(gold: Dict, result: Dict) -> bool:
    """Validator status match."""
    gold_val = gold.get("validator")
    pred_val = result.get("validator")
    if gold_val is None:
        return True
    return gold_val == pred_val


# ============================================================
# Bootstrap confidence interval
# ============================================================

def bootstrap_ci(scores: List[float], n_bootstrap: int = 1000, ci: float = 0.95) -> Tuple[float, float, float]:
    """Bootstrap confidence interval for a list of 0/1 scores."""
    if not scores:
        return 0.0, 0.0, 0.0
    arr = np.array(scores)
    means = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(arr, size=len(arr), replace=True)
        means.append(np.mean(sample))
    lower = np.percentile(means, (1 - ci) / 2 * 100)
    upper = np.percentile(means, (1 + ci) / 2 * 100)
    return float(np.mean(arr)), float(lower), float(upper)


# ============================================================
# Main evaluation loop
# ============================================================

def evaluate(
    gold_path: str,
    no_explain: bool = True,
    forced_domain: Optional[str] = None,
) -> Dict[str, Any]:
    """Run full evaluation and return results dict."""
    gold_set = load_gold_set(gold_path)
    print(f"\nLoaded {len(gold_set)} test cases from {gold_path}\n")

    results = []
    domain_scores = []
    table_scores = []
    intent_scores = []
    entity_f1_scores = []
    sql_scores = []
    validator_scores = []
    total_tp = total_fp = total_fn = 0
    entity_type_stats: Dict[str, Dict[str, int]] = {}

    for i, entry in enumerate(gold_set, 1):
        qid = entry.get("id", f"q{i}")
        question = entry["question"]
        gold = entry["gold"]
        tags = entry.get("tags", [])
        difficulty = entry.get("difficulty", "")

        print(f"[{i}/{len(gold_set)}] {qid}: {question[:60]}...")

        # Run pipeline
        try:
            pipeline_result = run_pipeline(
                question=question,
                explain=not no_explain,
                forced_domain=forced_domain,
            )
        except Exception as e:
            pipeline_result = {"error": str(e), "domain": None, "tables": [], "intent": None, "entities": {}, "sql": None, "validator": None}

        # Evaluate each component
        d_ok = eval_domain(gold, pipeline_result)
        t_ok = eval_tables(gold, pipeline_result)
        i_ok = eval_intent(gold, pipeline_result)
        ent_result = eval_entities(gold, pipeline_result)
        sql_result = eval_sql_contains(gold, pipeline_result)
        v_ok = eval_validator(gold, pipeline_result)

        domain_scores.append(1.0 if d_ok else 0.0)
        table_scores.append(1.0 if t_ok else 0.0)
        intent_scores.append(1.0 if i_ok else 0.0)
        entity_f1_scores.append(ent_result["f1"])
        sql_scores.append(1.0 if sql_result["pass"] else 0.0)
        validator_scores.append(1.0 if v_ok else 0.0)

        total_tp += ent_result["tp"]
        total_fp += ent_result["fp"]
        total_fn += ent_result["fn"]

        # Per entity-type stats
        for key, status in ent_result["details"].items():
            if key not in entity_type_stats:
                entity_type_stats[key] = {"tp": 0, "fp": 0, "fn": 0}
            if status == "TP":
                entity_type_stats[key]["tp"] += 1
            elif status.startswith("FP"):
                entity_type_stats[key]["fp"] += 1
            elif status.startswith("FN"):
                entity_type_stats[key]["fn"] += 1

        # Status line
        status_parts = []
        if not d_ok:
            status_parts.append(f"domain({gold.get('domain')}->{pipeline_result.get('domain')})")
        if not i_ok:
            status_parts.append(f"intent({gold.get('intent', '')[:30]}->{(pipeline_result.get('intent') or '')[:30]})")
        if not t_ok:
            status_parts.append(f"tables")
        if ent_result["f1"] < 1.0:
            status_parts.append(f"entities(F1={ent_result['f1']:.2f})")
        if not sql_result["pass"]:
            status_parts.append(f"sql(missing={sql_result['missing']})")

        if status_parts:
            print(f"  FAIL: {', '.join(status_parts)}")
        else:
            print(f"  PASS")

        results.append({
            "id": qid,
            "question": question,
            "tags": tags,
            "difficulty": difficulty,
            "domain": {"gold": gold.get("domain"), "pred": pipeline_result.get("domain"), "pass": d_ok},
            "tables": {"gold": gold.get("tables", []), "pred": pipeline_result.get("tables", []), "pass": t_ok},
            "intent": {"gold": gold.get("intent"), "pred": pipeline_result.get("intent"), "pass": i_ok},
            "entities": {
                "gold": gold.get("entities", {}),
                "pred": pipeline_result.get("entities", {}),
                "precision": ent_result["precision"],
                "recall": ent_result["recall"],
                "f1": ent_result["f1"],
                "details": ent_result["details"],
            },
            "sql": {
                "pred": pipeline_result.get("sql"),
                "contains_pass": sql_result["pass"],
                "matched": sql_result["matched"],
                "total": sql_result["total"],
                "missing": sql_result["missing"],
            },
            "validator": {"gold": gold.get("validator"), "pred": pipeline_result.get("validator"), "pass": v_ok},
            "error": pipeline_result.get("error"),
        })

    # Aggregate metrics
    n = len(gold_set)
    global_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    global_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    global_f1 = 2 * global_p * global_r / (global_p + global_r) if (global_p + global_r) > 0 else 0.0

    # Per entity-type P/R/F1
    entity_type_metrics = {}
    for etype, stats in sorted(entity_type_stats.items()):
        tp, fp, fn = stats["tp"], stats["fp"], stats["fn"]
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        entity_type_metrics[etype] = {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3), "support": tp + fn}

    # Bootstrap CIs
    domain_mean, domain_lo, domain_hi = bootstrap_ci(domain_scores)
    intent_mean, intent_lo, intent_hi = bootstrap_ci(intent_scores)
    sql_mean, sql_lo, sql_hi = bootstrap_ci(sql_scores)

    # Error analysis
    error_groups: Dict[str, List[str]] = {"domain": [], "tables": [], "intent": [], "entities": [], "sql": [], "validator": []}
    for r in results:
        qid = r["id"]
        if not r["domain"]["pass"]:
            error_groups["domain"].append(qid)
        if not r["tables"]["pass"]:
            error_groups["tables"].append(qid)
        if not r["intent"]["pass"]:
            error_groups["intent"].append(qid)
        if r["entities"]["f1"] < 1.0:
            error_groups["entities"].append(qid)
        if not r["sql"]["contains_pass"]:
            error_groups["sql"].append(qid)
        if not r["validator"]["pass"]:
            error_groups["validator"].append(qid)

    scorecard = {
        "timestamp": datetime.now().isoformat(),
        "gold_path": gold_path,
        "total_cases": n,
        "metrics": {
            "domain_routing": {
                "accuracy": round(domain_mean * 100, 1),
                "correct": int(sum(domain_scores)),
                "total": n,
                "ci_95": [round(domain_lo * 100, 1), round(domain_hi * 100, 1)],
            },
            "table_selection": {
                "accuracy": round(sum(table_scores) / n * 100, 1) if n else 0,
                "correct": int(sum(table_scores)),
                "total": n,
            },
            "intent_detection": {
                "accuracy": round(intent_mean * 100, 1),
                "correct": int(sum(intent_scores)),
                "total": n,
                "ci_95": [round(intent_lo * 100, 1), round(intent_hi * 100, 1)],
            },
            "entity_extraction": {
                "precision": round(global_p * 100, 1),
                "recall": round(global_r * 100, 1),
                "f1": round(global_f1 * 100, 1),
                "avg_f1": round(sum(entity_f1_scores) / n * 100, 1) if n else 0,
                "per_type": entity_type_metrics,
            },
            "sql_contains": {
                "accuracy": round(sql_mean * 100, 1),
                "correct": int(sum(sql_scores)),
                "total": n,
                "ci_95": [round(sql_lo * 100, 1), round(sql_hi * 100, 1)],
            },
            "validator": {
                "accuracy": round(sum(validator_scores) / n * 100, 1) if n else 0,
                "correct": int(sum(validator_scores)),
                "total": n,
            },
        },
        "error_analysis": {k: {"count": len(v), "cases": v} for k, v in error_groups.items()},
        "details": results,
    }

    return scorecard


# ============================================================
# Output
# ============================================================

def print_scorecard(sc: Dict[str, Any]):
    """Print formatted scorecard to console."""
    m = sc["metrics"]
    n = sc["total_cases"]

    print(f"\n{'=' * 60}")
    print(f"  PIPELINE EVALUATION SCORECARD")
    print(f"  {sc['timestamp']} | {n} test cases")
    print(f"{'=' * 60}\n")

    print("COMPONENT METRICS")
    print("-" * 50)

    dr = m["domain_routing"]
    print(f"  Domain Routing:     {dr['accuracy']}% ({dr['correct']}/{dr['total']})  CI95=[{dr['ci_95'][0]}%, {dr['ci_95'][1]}%]")

    ts = m["table_selection"]
    print(f"  Table Selection:    {ts['accuracy']}% ({ts['correct']}/{ts['total']})")

    it = m["intent_detection"]
    print(f"  Intent Detection:   {it['accuracy']}% ({it['correct']}/{it['total']})  CI95=[{it['ci_95'][0]}%, {it['ci_95'][1]}%]")

    ee = m["entity_extraction"]
    print(f"  Entity Extraction:")
    print(f"    Global:           P={ee['precision']}% R={ee['recall']}% F1={ee['f1']}%")
    print(f"    Avg per-query F1: {ee['avg_f1']}%")
    if ee["per_type"]:
        print(f"    Per-type breakdown:")
        for etype, em in ee["per_type"].items():
            print(f"      {etype:20s} P={em['precision']:.0%} R={em['recall']:.0%} F1={em['f1']:.0%} (n={em['support']})")

    sq = m["sql_contains"]
    print(f"  SQL Contains:       {sq['accuracy']}% ({sq['correct']}/{sq['total']})  CI95=[{sq['ci_95'][0]}%, {sq['ci_95'][1]}%]")

    va = m["validator"]
    print(f"  Validator:          {va['accuracy']}% ({va['correct']}/{va['total']})")

    # Error analysis
    ea = sc["error_analysis"]
    print(f"\nERROR ANALYSIS")
    print("-" * 50)
    for comp, info in ea.items():
        if info["count"] > 0:
            print(f"  {comp:20s} {info['count']} failures: {', '.join(info['cases'][:5])}")

    print(f"\n{'=' * 60}\n")


def save_results(sc: Dict[str, Any]):
    """Save results to evaluation/results/{timestamp}.json."""
    results_dir = os.path.join(_PROJECT_ROOT, "evaluation", "results")
    os.makedirs(results_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(results_dir, f"{ts}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(sc, f, ensure_ascii=False, indent=2, default=str)

    print(f"Results saved to: {path}")
    return path


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Evaluate Text2SQL Pipeline")
    parser.add_argument("--gold", default=os.path.join(_PROJECT_ROOT, "data", "evaluation", "gold_test_set.jsonl"),
                        help="Path to gold test set JSONL")
    parser.add_argument("--no-explain", action="store_true", help="Skip explain step (faster)")
    parser.add_argument("--domain", help="Force a specific domain (debug)")
    args = parser.parse_args()

    if not os.path.exists(args.gold):
        print(f"ERROR: Gold test set not found: {args.gold}")
        sys.exit(1)

    start = time.time()
    scorecard = evaluate(
        gold_path=args.gold,
        no_explain=args.no_explain,
        forced_domain=args.domain,
    )
    elapsed = round(time.time() - start, 2)
    scorecard["elapsed_seconds"] = elapsed

    print_scorecard(scorecard)
    save_results(scorecard)
    print(f"Total evaluation time: {elapsed}s")


if __name__ == "__main__":
    main()
