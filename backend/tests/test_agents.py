import uuid

from app.analysis import (
    AnalyzerAgent,
    ComplianceAgent,
    DueDiligenceOrchestrator,
    FinancialDataExtractor,
    RatioCalculator,
    ReportAgent,
    RiskAgent,
)
from app.analysis.agents.base import AgentContext
from app.analysis.agents.compliance import ComplianceData
from app.analysis.agents.risk import RiskData
from app.llm import FakeLLM
from app.models import Document, DocumentChunk


def _doc(filename: str = "acme.pdf") -> Document:
    return Document(
        id=str(uuid.uuid4()),
        filename=filename,
        storage_key="key",
        status="ready",
    )


def _chunk(document_id: str, content: str, page: int = 1) -> DocumentChunk:
    return DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=document_id,
        chunk_index=0,
        page_number=page,
        section="",
        content=content,
        token_count=0,
    )


def _context() -> AgentContext:
    doc = _doc()
    chunks = [
        _chunk(doc.id, "Total Assets: 1,250,000"),
        _chunk(doc.id, "Current Assets: 500,000"),
        _chunk(doc.id, "Total Liabilities: 750,000"),
        _chunk(doc.id, "Current Liabilities: 300,000"),
        _chunk(doc.id, "Shareholders' Equity: 500,000"),
        _chunk(doc.id, "Revenue: 1,500,000"),
        _chunk(doc.id, "Net Income: 180,000"),
        _chunk(doc.id, "The company faces ongoing litigation and mentions a going concern."),
    ]
    financials = FinancialDataExtractor().extract(chunks, [doc])
    ratios = RatioCalculator().calculate(financials)
    return AgentContext(documents=[doc], chunks=chunks, financials=financials, ratios=ratios)


def test_analyzer_agent_reports_ratios_and_trends():
    result = AnalyzerAgent().run(_context())
    assert result.success
    assert result.data.ratios
    assert result.citations
    names = {r.name for r in result.data.ratios}
    assert "Current Ratio" in names


def test_risk_agent_flags_litigation_and_going_concern():
    result = RiskAgent().run(_context())
    assert isinstance(result.data, RiskData)
    findings = " ".join(f.finding for f in result.data.red_flags)
    assert "Litigation" in findings
    assert "Going-concern" in findings
    assert result.data.source_chunk_ids


def test_compliance_agent_marks_missing_items():
    doc = _doc()
    chunks = [_chunk(doc.id, "Revenue: 1,000,000")]
    financials = FinancialDataExtractor().extract(chunks, [doc])
    context = AgentContext(documents=[doc], chunks=chunks, financials=financials)
    result = ComplianceAgent().run(context)
    assert isinstance(result.data, ComplianceData)
    assert any(i.status == "present" for i in result.data.items)
    assert any(i.status == "missing" for i in result.data.items)
    assert result.data.completion_pct > 0


def test_report_agent_compiles_all_sections():
    context = _context()
    analyzer = AnalyzerAgent().run(context)
    risk = RiskAgent().run(context)
    compliance = ComplianceAgent().run(context)
    context.analysis = analyzer.data
    context.risk = risk.data
    context.compliance = compliance.data

    result = ReportAgent(llm=None).run(context)
    assert result.success
    report = result.data
    assert report.title.startswith("Financial Due Diligence Report")
    assert report.document_count == 1
    assert "financial_analysis" in report.sections
    assert "risk" in report.sections
    assert "compliance" in report.sections
    assert report.source_chunk_ids


def test_orchestrator_runs_full_workflow():
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
    result = DueDiligenceOrchestrator(llm=FakeLLM()).run([doc], chunks)
    assert result.analyzer.success
    assert result.risk.success
    assert result.compliance.success
    assert result.report.success
    report = result.report_data
    assert report is not None
    assert report.sections["financial_analysis"]
    assert report.source_chunk_ids


def test_orchestrator_with_llm_generates_executive_summary():
    doc = _doc()
    chunks = [_chunk(doc.id, "Revenue: 1,500,000"), _chunk(doc.id, "Net Income: 180,000")]
    result = DueDiligenceOrchestrator(llm=FakeLLM()).run([doc], chunks)
    report = result.report_data
    assert report is not None
    assert "summary" in report.executive_summary.lower()
