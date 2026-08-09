from app.evaluation import EvaluationDataset, EvaluationQuestion, evaluate_rag
from app.qa import get_qa_service
from tests.helpers import make_balance_sheet_pdf, wait_for_status


def test_evaluate_rag_end_to_end(client):
    resp = client.post(
        "/api/v1/documents",
        files={"file": ("eval.pdf", make_balance_sheet_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    wait_for_status(client, doc_id)

    chunks = client.get(f"/api/v1/documents/{doc_id}/chunks").json()
    assert chunks, "expected the document to be chunked"

    golden = [c for c in chunks if "Total Assets" in c["content"]]
    assert golden, "expected a chunk mentioning total assets"
    golden_id = golden[0]["id"]

    dataset = EvaluationDataset(
        questions=[
            EvaluationQuestion(
                question="What were the company's total assets?",
                golden_chunk_ids=[golden_id],
                golden_answer_terms=["assets"],
            )
        ]
    )

    report = evaluate_rag(dataset, get_qa_service(), top_k=8)
    summary = report.summary()

    assert report.results[0].recall_at_k == 1.0
    assert summary["retrieval_recall_at_k"] == 1.0
    assert summary["groundedness"] == 1.0
    assert summary["mrr_at_k"] > 0

    client.delete(f"/api/v1/documents/{doc_id}")
