from app.evaluation import EvaluationDataset, EvaluationQuestion
from app.evaluation.metrics import (
    answer_hit_rate,
    citation_accuracy,
    groundedness,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)


def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], ["a", "d"], k=3) == 0.5
    assert recall_at_k(["a", "b", "c"], ["a"], k=1) == 1.0
    assert recall_at_k(["a"], ["b", "c"], k=2) == 0.0
    assert recall_at_k([], ["a"], k=5) == 0.0
    assert recall_at_k(["a"], [], k=5) == 0.0


def test_precision_at_k():
    assert precision_at_k(["a", "b", "c"], ["a"], k=3) == 1 / 3
    assert precision_at_k(["x", "a"], ["a"], k=1) == 0.0
    assert precision_at_k([], ["a"], k=3) == 0.0


def test_mrr_at_k():
    assert mean_reciprocal_rank(["x", "y", "a"], ["a"], k=3) == 1 / 3
    assert mean_reciprocal_rank(["a"], ["a"], k=3) == 1.0
    assert mean_reciprocal_rank(["x"], ["a"], k=3) == 0.0


def test_groundedness_and_citation_accuracy():
    assert groundedness(["c1"]) == 1.0
    assert groundedness([]) == 0.0
    assert citation_accuracy(["c1", "c2"], ["c1"]) == 0.5
    assert citation_accuracy([], ["c1"]) == 0.0
    assert citation_accuracy(["c1"], []) == 0.0


def test_answer_hit_rate():
    assert answer_hit_rate("Total assets were 1.25M.", ["total assets", "1.25m"]) == 1.0
    assert answer_hit_rate("Nothing here.", ["revenue"]) == 0.0
    assert answer_hit_rate("x", []) == 0.0


def test_dataset_roundtrip():
    dataset = EvaluationDataset(
        questions=[
            EvaluationQuestion(
                question="What is revenue?",
                golden_chunk_ids=["c1", "c2"],
                golden_answer_terms=["revenue"],
            )
        ]
    )
    assert EvaluationDataset.from_dict(dataset.to_dict()) == dataset
