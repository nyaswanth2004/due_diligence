from tests.helpers import make_balance_sheet_pdf, wait_for_status


def _upload_balance_sheet(client) -> dict:
    resp = client.post(
        "/api/v1/documents",
        files={"file": ("Acme_BalanceSheet_2024.pdf", make_balance_sheet_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    done = wait_for_status(client, resp.json()["id"])
    assert done["status"] == "ready", done
    return done


def test_qa_end_to_end_with_citations(client):
    document = _upload_balance_sheet(client)

    resp = client.post(
        "/api/v1/qa",
        json={
            "question": "What are the total assets?",
            "document_ids": [document["id"]],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"]
    assert body["context"], "context must be non-empty"
    assert body["citations"], "citations must be non-empty"

    context_ids = {c["chunk_id"] for c in body["context"]}
    assert all(c["chunk_id"] in context_ids for c in body["citations"])
    assert body["dropped_citations"] == []
    assert not body["unanswerable"]

    first = body["citations"][0]
    assert first["filename"] == "Acme_BalanceSheet_2024.pdf"
    assert first["doc_type"] == "balance_sheet"
    assert first["page_number"] >= 1


def test_qa_scoped_to_missing_document_is_unanswerable(client):
    resp = client.post(
        "/api/v1/qa",
        json={"question": "What are the total assets?", "document_ids": ["does-not-exist"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["unanswerable"] is True
    assert body["context"] == []
    assert body["citations"] == []
    assert body["answer"]


def test_qa_validates_request(client):
    resp = client.post("/api/v1/qa", json={"question": ""})
    assert resp.status_code == 422
