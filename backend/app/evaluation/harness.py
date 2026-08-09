"""Runs a golden dataset through retrieval + grounded QA and scores quality."""

import statistics
from dataclasses import dataclass, field

from app.evaluation.dataset import EvaluationDataset
from app.evaluation.metrics import (
    answer_hit_rate,
    citation_accuracy,
    groundedness,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)
from app.qa import QAService


@dataclass
class QuestionResult:
    question: str
    golden_chunk_ids: list[str]
    retrieved_ids: list[str]
    recall_at_k: float
    precision_at_k: float
    mrr_at_k: float
    grounded: bool
    citation_accuracy: float
    answer_hit_rate: float
    answer: str = ""
    dropped_citations: list[str] = field(default_factory=list)


@dataclass
class EvaluationReport:
    results: list[QuestionResult]
    k: int

    def _mean(self, values: list[float]) -> float:
        return round(statistics.fmean(values), 4) if values else 0.0

    def summary(self) -> dict:
        counts = len(self.results)
        return {
            "questions": counts,
            "top_k": self.k,
            "retrieval_recall_at_k": self._mean([r.recall_at_k for r in self.results]),
            "retrieval_precision_at_k": self._mean([r.precision_at_k for r in self.results]),
            "mrr_at_k": self._mean([r.mrr_at_k for r in self.results]),
            "groundedness": self._mean([1.0 if r.grounded else 0.0 for r in self.results]),
            "citation_accuracy": self._mean([r.citation_accuracy for r in self.results]),
            "answer_hit_rate": self._mean([r.answer_hit_rate for r in self.results]),
        }


def evaluate_rag(
    dataset: EvaluationDataset,
    qa_service: QAService,
    *,
    top_k: int = 8,
) -> EvaluationReport:
    """Runs each question through QAService and scores retrieval + answering.

    Requires document_ids=None so the full index is searched; golden ids are
    the authoritative chunk ids captured when building the dataset.
    """
    results: list[QuestionResult] = []
    for entry in dataset.questions:
        response = qa_service.answer(entry.question, top_k=top_k)
        retrieved_ids = [c.chunk_id for c in response.context]
        valid_citations = [c.chunk_id for c in response.citations]

        results.append(
            QuestionResult(
                question=entry.question,
                golden_chunk_ids=entry.golden_chunk_ids,
                retrieved_ids=retrieved_ids,
                recall_at_k=recall_at_k(retrieved_ids, entry.golden_chunk_ids, top_k),
                precision_at_k=precision_at_k(retrieved_ids, entry.golden_chunk_ids, top_k),
                mrr_at_k=mean_reciprocal_rank(retrieved_ids, entry.golden_chunk_ids, top_k),
                grounded=groundedness(valid_citations) == 1.0,
                citation_accuracy=citation_accuracy(valid_citations, entry.golden_chunk_ids),
                answer_hit_rate=answer_hit_rate(response.answer, entry.golden_answer_terms),
                answer=response.answer,
                dropped_citations=response.dropped_citations,
            )
        )
    return EvaluationReport(results=results, k=top_k)
