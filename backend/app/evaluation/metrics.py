"""Retrieval and answer-quality metrics."""


def recall_at_k(retrieved_ids: list[str], golden_ids: list[str], k: int) -> float:
    if not golden_ids:
        return 0.0
    hits = set(retrieved_ids[:k]) & set(golden_ids)
    return len(hits) / len(golden_ids)


def precision_at_k(retrieved_ids: list[str], golden_ids: list[str], k: int) -> float:
    retrieved = retrieved_ids[:k]
    if not retrieved:
        return 0.0
    hits = set(retrieved) & set(golden_ids)
    return len(hits) / len(retrieved)


def mean_reciprocal_rank(retrieved_ids: list[str], golden_ids: list[str], k: int) -> float:
    golden = set(golden_ids)
    for index, chunk_id in enumerate(retrieved_ids[:k]):
        if chunk_id in golden:
            return 1.0 / (index + 1)
    return 0.0


def groundedness(valid_citations: list[str]) -> float:
    """Whether the answer is supported by at least one verified citation."""
    return 1.0 if valid_citations else 0.0


def citation_accuracy(valid_citations: list[str], golden_ids: list[str]) -> float:
    """Fraction of the answer's valid citations that are golden-relevant."""
    if not valid_citations:
        return 0.0
    if not golden_ids:
        return 0.0
    hits = set(valid_citations) & set(golden_ids)
    return len(hits) / len(valid_citations)


def answer_hit_rate(answer: str, expected_terms: list[str]) -> float:
    """Fraction of expected substrings present in the answer."""
    if not expected_terms:
        return 0.0
    lowered = answer.lower()
    hits = sum(1 for term in expected_terms if term.lower() in lowered)
    return hits / len(expected_terms)
