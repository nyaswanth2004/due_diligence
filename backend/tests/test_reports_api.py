import pytest

from tests.helpers import make_balance_sheet_pdf, make_income_statement_xlsx, wait_for_status


@pytest.fixture
def uploaded_documents(client):
    ids = []
    for payload, filename in [
        (make_balance_sheet_pdf(), "balance.pdf"),
        (make_income_statement_xlsx(), "income.xlsx"),
    ]:
        resp = client.post(
            "/api/v1/documents",
            files={"file": (filename, payload, "application/octet-stream")},
        )
        assert resp.status_code == 201, resp.text
        ids.append(resp.json()["id"])
    for document_id in ids:
        wait_for_status(client, document_id)
    return ids


def test_generate_report_api(client, uploaded_documents):
    resp = client.post("/api/v1/reports/generate", json={"document_ids": uploaded_documents})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["title"].startswith("Financial Due Diligence Report")
    assert body["document_count"] == 2
    assert "financial_analysis" in body["sections"]
    assert "compliance" in body["sections"]
    assert body["financial_metrics"]["revenue"]["value"] == 1_500_000


def test_generate_report_requires_documents(client):
    resp = client.post("/api/v1/reports/generate", json={"document_ids": ["missing-id"]})
    assert resp.status_code == 404
    assert "No documents" in resp.json()["detail"]


def test_reports_list_and_get(client, uploaded_documents):
    client.post("/api/v1/reports/generate", json={"document_ids": uploaded_documents})

    resp = client.get("/api/v1/reports")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    report_id = resp.json()["items"][0]["id"]
    resp = client.get(f"/api/v1/reports/{report_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["summary"]


def test_get_missing_report_returns_404(client):
    resp = client.get("/api/v1/reports/nope")
    assert resp.status_code == 404
