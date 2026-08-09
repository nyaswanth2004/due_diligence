from tests.helpers import (
    make_balance_sheet_pdf,
    make_cash_flow_csv,
    make_income_statement_xlsx,
    wait_for_status,
)


def test_health(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_rejects_unsupported_type(client):
    resp = client.post("/api/v1/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 415


def test_pdf_end_to_end(client):
    resp = client.post(
        "/api/v1/documents",
        files={"file": ("Acme_BalanceSheet_2024.pdf", make_balance_sheet_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    document = resp.json()
    assert document["status"] == "pending"

    done = wait_for_status(client, document["id"])
    assert done["status"] == "ready", done
    assert done["doc_type"] == "balance_sheet"
    assert done["page_count"] == 1
    assert done["chunk_count"] >= 1

    chunks = client.get(f"/api/v1/documents/{document['id']}/chunks")
    assert chunks.status_code == 200
    body = chunks.json()
    assert len(body) >= 1
    assert body[0]["page_number"] == 1
    assert body[0]["document_id"] == document["id"]


def test_xlsx_end_to_end(client):
    resp = client.post(
        "/api/v1/documents",
        files={"file": ("Income_Statement_2024.xlsx", make_income_statement_xlsx(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 201, resp.text
    done = wait_for_status(client, resp.json()["id"])
    assert done["status"] == "ready", done
    assert done["doc_type"] == "income_statement"
    assert done["page_count"] == 1


def test_csv_end_to_end(client):
    resp = client.post(
        "/api/v1/documents",
        files={"file": ("CashFlow.csv", make_cash_flow_csv(), "text/csv")},
    )
    assert resp.status_code == 201, resp.text
    done = wait_for_status(client, resp.json()["id"])
    assert done["status"] == "ready", done
    assert done["doc_type"] == "cash_flow_statement"


def test_list_and_delete(client):
    resp = client.post(
        "/api/v1/documents",
        files={"file": ("Acme_BalanceSheet_2024.pdf", make_balance_sheet_pdf(), "application/pdf")},
    )
    document = resp.json()
    wait_for_status(client, document["id"])

    listing = client.get("/api/v1/documents")
    assert listing.status_code == 200
    ids = [item["id"] for item in listing.json()["items"]]
    assert document["id"] in ids

    filtered = client.get("/api/v1/documents", params={"status_filter": "ready"})
    assert filtered.status_code == 200
    assert all(item["status"] == "ready" for item in filtered.json()["items"])

    delete = client.delete(f"/api/v1/documents/{document['id']}")
    assert delete.status_code == 204
    assert client.get(f"/api/v1/documents/{document['id']}").status_code == 404
