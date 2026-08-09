from app.ingestion.classifier import DocumentClassifier


def test_classify_balance_sheet_by_content():
    text = (
        "BALANCE SHEET\n"
        "Current Assets: 100,000\n"
        "Total Assets: 500,000\n"
        "Total Liabilities: 200,000\n"
        "Shareholders' Equity: 300,000\n"
    )
    doc_type, confidence = DocumentClassifier().classify("some_report.pdf", text)
    assert doc_type == "balance_sheet"
    assert confidence >= 0.15


def test_classify_cash_flow_by_content():
    text = (
        "STATEMENT OF CASH FLOWS\n"
        "Net cash from operating activities: 50,000\n"
        "Net cash from investing activities: -20,000\n"
        "Net cash from financing activities: -5,000\n"
    )
    doc_type, _ = DocumentClassifier().classify("report.pdf", text)
    assert doc_type == "cash_flow_statement"


def test_classify_by_filename():
    doc_type, confidence = DocumentClassifier().classify("BalanceSheet_FY2024.xlsx", "")
    assert doc_type == "balance_sheet"
    assert confidence >= 0.5


def test_unknown_content():
    doc_type, confidence = DocumentClassifier().classify("misc.pdf", "lorem ipsum dolor sit amet")
    assert doc_type == "unknown"
    assert confidence == 0.0
