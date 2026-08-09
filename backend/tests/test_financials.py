import uuid

from app.analysis.financials import FinancialDataExtractor
from app.analysis.ratios import RatioCalculator
from app.models import Document, DocumentChunk


def _doc(filename: str = "acme.pdf") -> Document:
    return Document(
        id=str(uuid.uuid4()),
        filename=filename,
        storage_key="key",
        status="ready",
    )


def _chunk(document_id: str, content: str, page: int = 1, section: str = "") -> DocumentChunk:
    return DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=document_id,
        chunk_index=0,
        page_number=page,
        section=section,
        content=content,
        token_count=0,
    )


def test_extractor_captures_line_items_with_provenance():
    doc = _doc()
    chunks = [
        _chunk(doc.id, "Total Assets: 1,250,000", page=1),
        _chunk(doc.id, "Total Liabilities: 750,000", page=1),
        _chunk(doc.id, "Revenue: 1,500,000", page=2),
        _chunk(doc.id, "Net Income: 180,000", page=2),
    ]
    data = FinancialDataExtractor().extract(chunks, [doc])

    assert data.first("revenue").value == 1_500_000
    assert data.first("net_income").value == 180_000
    assert data.first("total_assets").value == 1_250_000
    assert data.first("total_liabilities").value == 750_000

    assets = data.first("total_assets")
    assert assets.chunk_id
    assert assets.page == 1
    assert assets.document_id == doc.id
    assert assets.filename == "acme.pdf"


def test_extractor_handles_prior_year_and_negative_values():
    doc = _doc()
    chunk = _chunk(doc.id, "Total Revenue: 1,500,000 2023: 1,400,000", page=1)
    data = FinancialDataExtractor().extract([chunk], [doc])

    item = data.first("revenue")
    assert item.value == 1_500_000
    assert item.prior_value == 1_400_000


def test_extractor_skips_lines_without_numbers():
    doc = _doc()
    chunk = _chunk(doc.id, "Revenue recognition policy is consistent.", page=1)
    data = FinancialDataExtractor().extract([chunk], [doc])
    assert not data.all("revenue")


def test_ratio_calculator_emits_only_supported_ratios():
    doc = _doc()
    chunks = [
        _chunk(doc.id, "Total Assets: 1,250,000"),
        _chunk(doc.id, "Current Assets: 500,000"),
        _chunk(doc.id, "Total Liabilities: 750,000"),
        _chunk(doc.id, "Current Liabilities: 300,000"),
        _chunk(doc.id, "Shareholders' Equity: 500,000"),
        _chunk(doc.id, "Revenue: 1,500,000"),
        _chunk(doc.id, "Net Income: 180,000"),
    ]
    data = FinancialDataExtractor().extract(chunks, [doc])
    ratios = RatioCalculator().calculate(data)
    names = {r.name for r in ratios}

    assert {"Current Ratio", "Debt-to-Equity", "Debt Ratio",
            "Net Profit Margin", "Return on Assets", "Return on Equity"} <= names

    by_name = {r.name: r for r in ratios}
    assert by_name["Current Ratio"].value == 1.67
    assert by_name["Debt-to-Equity"].value == 1.5
    assert by_name["Net Profit Margin"].value == 0.12


def test_ratio_calculator_high_risk_signals():
    doc = _doc()
    chunks = [
        _chunk(doc.id, "Total Assets: 1,000,000"),
        _chunk(doc.id, "Total Liabilities: 900,000"),
        _chunk(doc.id, "Current Assets: 100,000"),
        _chunk(doc.id, "Current Liabilities: 200,000"),
        _chunk(doc.id, "Shareholders' Equity: 100,000"),
        _chunk(doc.id, "Revenue: 1,000,000"),
        _chunk(doc.id, "Net Income: -50,000"),
    ]
    data = FinancialDataExtractor().extract(chunks, [doc])
    ratios = RatioCalculator().calculate(data)
    by_name = {r.name: r for r in ratios}

    assert by_name["Current Ratio"].risk_level == "high"
    assert by_name["Debt-to-Equity"].risk_level == "high"
    assert by_name["Debt Ratio"].risk_level == "high"
    assert by_name["Net Profit Margin"].risk_level == "high"


def test_ratio_calculator_no_invented_inputs():
    doc = _doc()
    chunks = [_chunk(doc.id, "Total Assets: 1,000,000")]
    data = FinancialDataExtractor().extract(chunks, [doc])
    ratios = RatioCalculator().calculate(data)
    assert ratios == []
