"""Evaluate RAG quality against a golden dataset.

Usage:
    .venv\\Scripts\\python -m scripts.evaluate --dataset golden.json --top-k 8

The golden dataset must reference actual chunk ids in the index. See
app/evaluation/dataset.py for the schema ({"questions": [{"question": ...,
"golden_chunk_ids": [...], "golden_answer_terms": [...]}]}).
"""

import argparse
import json
import sys

from app.evaluation import EvaluationDataset, evaluate_rag
from app.qa import get_qa_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RAG evaluation.")
    parser.add_argument("--dataset", required=True, help="Path to the golden JSON dataset.")
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args()

    dataset = EvaluationDataset.load(args.dataset)
    if not dataset.questions:
        print("error: dataset contains no questions", file=sys.stderr)
        return 1

    report = evaluate_rag(dataset, get_qa_service(), top_k=args.top_k)
    print(json.dumps(report.summary(), indent=2))

    for result in report.results:
        status = "OK" if result.recall_at_k == 1.0 else "FAIL"
        print(
            f"[{status}] recall@{report.k}={result.recall_at_k:.2f} "
            f"mrr@{report.k}={result.mrr_at_k:.2f} "
            f"grounded={result.grounded} "
            f"hit_rate={result.answer_hit_rate:.2f} :: {result.question}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
