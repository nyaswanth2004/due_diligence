import os
import tempfile

import pytest

from app.retrieval.hybrid import reciprocal_rank_fusion
from app.retrieval.vector_index import LocalVectorIndex


def _vec(*values: float) -> list[float]:
    return list(values)


class TestLocalVectorIndex:
    @staticmethod
    def _doc_of(index: LocalVectorIndex, chunk_id: str) -> str:
        return index._doc_of[chunk_id]

    def test_add_search_remove(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = LocalVectorIndex(path=os.path.join(tmp, "idx"))
            index.add("doc1", [("c1", _vec(1.0, 0.0, 0.0)), ("c2", _vec(0.0, 1.0, 0.0))])
            index.add("doc2", [("c3", _vec(0.0, 0.0, 1.0))])

            hits = index.search(_vec(1.0, 0.0, 0.0), top_k=2)
            assert hits[0][0] == "c1"
            assert len(hits) == 2

            filtered = index.search(_vec(0.0, 1.0, 0.0), top_k=5, document_ids={"doc1"})
            assert filtered[0][0] == "c2"
            assert all(self._doc_of(index, cid) == "doc1" for cid, _ in filtered)

            stats = index.statistics()
            assert stats["documents"] == 2
            assert stats["chunks"] == 3

            index.remove("doc1")
            assert index.statistics()["chunks"] == 1
            remaining = index.search(_vec(1.0, 0.0, 0.0), top_k=5)
            assert [c for c, _ in remaining] == ["c3"]

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "idx")
            index = LocalVectorIndex(path=path)
            index.add("doc1", [("c1", _vec(1.0, 0.0))])
            index.add("doc2", [("c2", _vec(0.0, 1.0))])

            reloaded = LocalVectorIndex(path=path)
            assert reloaded.statistics() == {"documents": 2, "chunks": 2}
            hits = reloaded.search(_vec(0.0, 1.0), top_k=1)
            assert hits[0][0] == "c2"

    def test_dimension_mismatch_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = LocalVectorIndex(path=os.path.join(tmp, "idx"))
            index.add("doc1", [("c1", _vec(1.0, 0.0))])
            with pytest.raises(ValueError):
                index.add("doc2", [("c2", _vec(1.0, 0.0, 0.0))])


class TestHybrid:
    def test_rrf_prefers_items_ranked_by_both_legs(self):
        vector_rank = ["a", "b", "c", "d"]
        keyword_rank = ["b", "d", "a"]
        fused = reciprocal_rank_fusion([vector_rank, keyword_rank], k=60)
        order = [cid for cid, _ in sorted(fused.items(), key=lambda pair: -pair[1])]
        assert order[0] == "b"
        assert set(order) == {"a", "b", "c", "d"}

    def test_rrf_k_smoothing(self):
        fused = reciprocal_rank_fusion([["x", "y"], ["y"]], k=60)
        assert fused["x"] == pytest.approx(1 / 61)
        assert fused["y"] == pytest.approx(1 / 61 + 1 / 62)
