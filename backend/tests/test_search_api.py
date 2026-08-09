from tests.helpers import make_balance_sheet_pdf, wait_for_status


def _upload_pdf(client, name: str = "Acme_BalanceSheet_2024.pdf") -> dict:
    resp = client.post(
        "/api/v1/documents",
        files={"file": (name, make_balance_sheet_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    done = wait_for_status(client, resp.json()["id"])
    assert done["status"] == "ready", done
    return done


def test_search_returns_provenance(client):
    document = _upload_pdf(client)

    resp = client.get("/api/v1/search", params={"q": "balance sheet total assets", "top_k": 20})
    assert resp.status_code == 200, resp.text
    hits = resp.json()
    assert any(hit["document_id"] == document["id"] for hit in hits)

    target = next(hit for hit in hits if hit["document_id"] == document["id"])
    assert target["filename"] == "Acme_BalanceSheet_2024.pdf"
    assert target["doc_type"] == "balance_sheet"
    assert target["page_number"] >= 1
    assert target["content"]


def test_search_scoped_to_document(client):
    doc_a = _upload_pdf(client, "Acme_BalanceSheet_2024.pdf")

    resp = client.get("/api/v1/search", params={"q": "total assets", "document_id": doc_a["id"]})
    assert resp.status_code == 200
    assert all(hit["document_id"] == doc_a["id"] for hit in resp.json())

    resp = client.get(
        "/api/v1/search",
        params={"q": "total assets", "document_id": "does-not-exist"},
    )
    assert resp.json() == []


def test_search_stats(client):
    _upload_pdf(client)
    resp = client.get("/api/v1/search/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["documents"] >= 1
    assert body["chunks"] >= 1
    assert body["backend"] == "local"
    assert body["embeddings"] == "hash"


def test_search_empty_index(client):
    resp = client.get("/api/v1/search", params={"q": "nonsense that surely matches nothing"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_search_deletes_document_from_index(client):
    document = _upload_pdf(client)
    assert client.delete(f"/api/v1/documents/{document['id']}").status_code == 204

    resp = client.get("/api/v1/search", params={"q": "total assets"})
    assert all(hit["document_id"] != document["id"] for hit in resp.json())
