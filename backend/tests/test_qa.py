import json
import re

from app.llm.client import FakeLLM, _UUID_RE
from app.qa.citation import CitationVerifier
from app.qa.prompts import build_messages
from app.qa.service import QAService, parse_llm_json
from app.schemas.qa import EvidenceChunk, QAMessage
from app.schemas.search import RetrievalHit


def _evidence(chunk_id: str = "11111111-1111-4111-8111-111111111111",
              content: str = "Total assets are 1,250,000.") -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=chunk_id,
        document_id="d1",
        filename="Acme_BalanceSheet_2024.pdf",
        doc_type="balance_sheet",
        page_number=1,
        section="Balance Sheet",
        content=content,
        score=0.9,
    )


def _hit(chunk_id: str = "11111111-1111-4111-8111-111111111111",
         content: str = "Total assets are 1,250,000.") -> RetrievalHit:
    return RetrievalHit(
        chunk_id=chunk_id,
        document_id="d1",
        filename="Acme_BalanceSheet_2024.pdf",
        doc_type="balance_sheet",
        page_number=1,
        section="Balance Sheet",
        content=content,
        score=0.9,
    )


class StubRetrieval:
    def __init__(self, hits):
        self._hits = hits

    def search(self, *args, **kwargs):
        return self._hits


class HallucinatingLLM(FakeLLM):
    def generate(self, messages, *, format=None, temperature=0.1):
        last = messages[-1]["content"]
        ids = list(dict.fromkeys(_UUID_RE.findall(last)))
        cited = ids[:1] if ids else []
        return json.dumps({"answer": "answer with a made-up citation", "citations": cited + ["hallucinated-id"]})


class ExplodingLLM(FakeLLM):
    def generate(self, messages, *, format=None, temperature=0.1):
        raise AssertionError("LLM must not be called when no context is retrieved")


class TestParseLlmJson:
    def test_plain_json(self):
        assert parse_llm_json('{"answer": "a", "citations": ["x"]}') == {"answer": "a", "citations": ["x"]}

    def test_fenced_json(self):
        raw = '```json\n{"answer": "a", "citations": []}\n```'
        assert parse_llm_json(raw) == {"answer": "a", "citations": []}

    def test_json_embedded_in_text(self):
        raw = 'Here you go: {"answer": "a", "citations": ["c1"]} hope that helps'
        assert parse_llm_json(raw)["citations"] == ["c1"]

    def test_garbage(self):
        assert parse_llm_json("totally not json") == {}


class TestCitationVerifier:
    def test_keeps_valid_drops_invalid_and_dedupes(self):
        report = CitationVerifier().verify(
            ["c1", "c2", "c1", "fake", "c3"],
            allowed_ids=["c1", "c2"],
        )
        assert report.valid == ["c1", "c2"]
        assert report.dropped == ["fake", "c3"]


class TestPrompts:
    def test_build_messages_includes_context_with_ids(self):
        messages = build_messages([_evidence("chunk-abc")], "What are total assets?", [])
        assert messages[0]["role"] == "system"
        last = messages[-1]["content"]
        assert "chunk-abc" in last
        assert "What are total assets?" in last
        assert "citations" in last

    def test_history_is_truncated_to_configured_limit(self):
        history = [QAMessage(role="user", content=f"turn {i}") for i in range(20)]
        messages = build_messages([_evidence()], "q", history)
        history_roles = [m for m in messages if m["role"] in ("user", "assistant")]
        assert len(history_roles) == 7  # 6 history turns + current question


class TestQAService:
    def test_grounded_answer_with_valid_citations(self):
        c1 = "11111111-1111-4111-8111-111111111111"
        c2 = "22222222-2222-4222-8222-222222222222"
        service = QAService(
            llm=FakeLLM(),
            retrieval=StubRetrieval([_hit(c1), _hit(c2, "Total liabilities are 750,000.")]),
        )
        response = service.answer("What are total assets?")
        assert response.answer
        assert [c.chunk_id for c in response.citations] == [c1, c2]
        assert response.dropped_citations == []
        assert not response.unanswerable
        assert response.citations[0].page_number == 1
        assert response.citations[0].filename == "Acme_BalanceSheet_2024.pdf"

    def test_hallucinated_citations_are_dropped(self):
        c1 = "11111111-1111-4111-8111-111111111111"
        service = QAService(
            llm=HallucinatingLLM(),
            retrieval=StubRetrieval([_hit(c1)]),
        )
        response = service.answer("What are total assets?")
        assert [c.chunk_id for c in response.citations] == [c1]
        assert response.dropped_citations == ["hallucinated-id"]

    def test_no_context_short_circuits_before_llm(self):
        service = QAService(llm=ExplodingLLM(), retrieval=StubRetrieval([]))
        response = service.answer("anything")
        assert response.unanswerable
        assert response.context == []
        assert response.answer
