"""RAG evaluation harness: dataset definition, metrics, and runner."""

from app.evaluation.dataset import EvaluationDataset, EvaluationQuestion
from app.evaluation.harness import EvaluationReport, evaluate_rag
from app.evaluation.metrics import (
    citation_accuracy,
    groundedness,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)

__all__ = [
    "EvaluationDataset",
    "EvaluationQuestion",
    "EvaluationReport",
    "citation_accuracy",
    "evaluate_rag",
    "groundedness",
    "mean_reciprocal_rank",
    "precision_at_k",
    "recall_at_k",
]
