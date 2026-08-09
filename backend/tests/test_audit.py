from tests.helpers import make_balance_sheet_pdf, make_income_statement_xlsx, wait_for_status


def test_upload_and_delete_are_audited(client):
    resp = client.post(
        "/api/v1/documents",
        files={"file": ("audit.pdf", make_balance_sheet_pdf(), "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    wait_for_status(client, doc_id)

    resp = client.delete(f"/api/v1/documents/{doc_id}")
    assert resp.status_code == 204

    audit = client.get("/api/v1/audit?action=document.upload&limit=50").json()
    assert any(item["resource_id"] == doc_id for item in audit["items"])

    audit = client.get("/api/v1/audit?action=document.delete&limit=50").json()
    assert any(item["resource_id"] == doc_id for item in audit["items"])


def test_search_and_qa_and_report_are_audited(client):
    ids = []
    for payload, filename in [
        (make_balance_sheet_pdf(), "b.pdf"),
        (make_income_statement_xlsx(), "i.xlsx"),
    ]:
        resp = client.post(
            "/api/v1/documents",
            files={"file": (filename, payload, "application/octet-stream")},
        )
        assert resp.status_code == 201, resp.text
        ids.append(resp.json()["id"])
    for document_id in ids:
        wait_for_status(client, document_id)

    client.get("/api/v1/search", params={"q": "assets"})
    audit = client.get("/api/v1/audit?action=document.search&limit=50").json()
    assert audit["total"] >= 1
    assert any("assets" in item["details"]["query"] for item in audit["items"])

    client.post("/api/v1/qa", json={"question": "What are total assets?"})
    audit = client.get("/api/v1/audit?action=qa.ask&limit=50").json()
    assert audit["total"] >= 1

    client.post("/api/v1/reports/generate", json={"document_ids": ids})
    audit = client.get("/api/v1/audit?action=report.generate&limit=50").json()
    assert audit["total"] >= 1

    for document_id in ids:
        client.delete(f"/api/v1/documents/{document_id}")


def test_audit_filter_by_username(client):
    resp = client.get("/api/v1/audit?username=testadmin&limit=50")
    assert resp.status_code == 200
    assert all(item["username"] == "testadmin" for item in resp.json()["items"])
