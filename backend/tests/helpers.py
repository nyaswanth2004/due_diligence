import io
import time

from fastapi.testclient import TestClient

from app.main import app


def make_balance_sheet_pdf() -> bytes:
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(72, 770, "Acme Corp Annual Report")
    c.drawString(72, 750, "Balance Sheet")
    c.drawString(72, 730, "As at December 31, 2024")
    c.drawString(72, 700, "Total Assets: 1,250,000")
    c.drawString(72, 680, "Current Assets: 500,000")
    c.drawString(72, 660, "Total Liabilities: 750,000")
    c.drawString(72, 640, "Current Liabilities: 300,000")
    c.drawString(72, 620, "Shareholders' Equity: 500,000")
    c.drawString(72, 590, "Notes to the financial statements:")
    c.drawString(72, 570, "The company maintains consistent accounting policies.")
    c.showPage()
    c.save()
    return buffer.getvalue()


def make_income_statement_xlsx() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Income Statement"
    ws.append(["Item", "2024", "2023"])
    ws.append(["Total Revenue", 1500000, 1400000])
    ws.append(["Gross Profit", 600000, 550000])
    ws.append(["Operating Income", 300000, 280000])
    ws.append(["Net Income", 180000, 160000])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def make_cash_flow_csv() -> bytes:
    return (
        "Statement of Cash Flows\n"
        "Cash Flow Item,2024,2023\n"
        "Operating Activities,200000,180000\n"
        "Investing Activities,-50000,-40000\n"
        "Financing Activities,-30000,-25000\n"
        "Net Cash,120000,115000\n"
    ).encode("utf-8")


def wait_for_status(client: TestClient, document_id: str, timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/api/v1/documents/{document_id}")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        if body["status"] in ("ready", "failed"):
            return body
        time.sleep(0.2)
    raise AssertionError(f"document {document_id} did not finish processing in {timeout}s")
