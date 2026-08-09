from typing import Iterable


def reciprocal_rank_fusion(rankings: list[Iterable[str]], k: int = 60) -> dict[str, float]:
    """Fuse multiple ranked chunk-id lists with Reciprocal Rank Fusion.

    RRF is rank-based (not score-based), so it needs no score normalisation
    between the vector and keyword legs. `k` is the smoothing constant.
    """
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (k + rank)
    return fused
