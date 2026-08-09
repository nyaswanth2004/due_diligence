"""Report agent: compiles agent findings into a structured due diligence report."""

from dataclasses import dataclass, field
from datetime import date

from app.analysis.agents.base import Agent, AgentContext, AgentResult
from app.analysis.agents.analyzer import AnalyzerData
from app.analysis.agents.compliance import ComplianceData
from app.analysis.agents.risk import RiskData
from app.core.config import settings
from app.llm.client import LLMClient

DEFAULT_NARRATIVE = (
    "This report was generated automatically from the extracted financial data. "
    "A narrative summary is not available; enable an LLM backend for narrative generation."
)


@dataclass
class ReportData:
    title: str
    generated_on: str
    document_count: int
    summary: str
    sections: dict[str, list[dict]]
    executive_summary: str = ""
    source_chunk_ids: list[str] = field(default_factory=list)


class ReportAgent(Agent):
    """Assembles the final report and optionally drafts an executive summary."""

    name = "report"

    def __init__(self, llm: LLMClient | None = None):
        self._llm = llm

    def run(self, context: AgentContext) -> AgentResult:
        analyzer = context.analysis
        risk = context.risk
        compliance = context.compliance

        summary_parts: list[str] = []
        if analyzer:
            for trend in analyzer.trends:
                summary_parts.append(trend.note)
        if risk:
            summary_parts.append(f"{len(risk.red_flags)} red flag(s) identified.")
        if compliance:
            summary_parts.append(
                f"Disclosure completeness is {compliance.completion_pct}%."
            )
        summary = " ".join(summary_parts) if summary_parts else "No financial data was extracted for this review."

        sections: dict[str, list[dict]] = {}
        if analyzer:
            sections["financial_analysis"] = [r.__dict__ for r in analyzer.ratios] + [
                t.__dict__ for t in analyzer.trends
            ]
        if risk:
            sections["risk"] = [f.__dict__ for f in risk.red_flags]
        if compliance:
            sections["compliance"] = [i.__dict__ for i in compliance.items] + [
                {"completion_pct": compliance.completion_pct}
            ]

        citation_ids = sorted({
            cid
            for section in sections.values()
            for entry in section
            if isinstance(entry, dict)
            for cid in (entry.get("source_chunk_ids") or [])
        })
        citation_ids = sorted(set(citation_ids))

        title = "Financial Due Diligence Report"
        if context.documents:
            title = f"Financial Due Diligence Report — {context.documents[0].filename}"

        data = ReportData(
            title=title,
            generated_on=date.today().isoformat(),
            document_count=len(context.documents),
            summary=summary,
            sections=sections,
            executive_summary=self._executive_summary(analyzer, risk, compliance),
            source_chunk_ids=citation_ids,
        )
        return AgentResult(agent=self.name, data=data, citations=citation_ids)

    def _executive_summary(
        self,
        analyzer: AnalyzerData | None,
        risk: RiskData | None,
        compliance: ComplianceData | None,
    ) -> str:
        if not settings.REPORT_NARRATIVE_ENABLED or self._llm is None:
            return DEFAULT_NARRATIVE

        try:
            return self._llm.generate_text(
                self._narrative_prompt(analyzer, risk, compliance),
                max_tokens=600,
            )
        except Exception:
            return DEFAULT_NARRATIVE

    @staticmethod
    def _narrative_prompt(
        analyzer: AnalyzerData | None,
        risk: RiskData | None,
        compliance: ComplianceData | None,
    ) -> str:
        lines = [
            "You are a financial due diligence analyst. Write a concise executive summary "
            "(max 6 sentences) of the target company based strictly on the structured facts below.",
        ]
        if analyzer:
            lines.append("RATIOS: " + " | ".join(
                f"{r.name}={r.value} ({r.interpretation})" for r in analyzer.ratios
            ))
            lines.append("TRENDS: " + " | ".join(t.note for t in analyzer.trends))
        if risk:
            lines.append("RISK: " + " | ".join(f.finding for f in risk.red_flags[:5]))
        if compliance:
            lines.append("COMPLIANCE: " + f"Disclosure completeness {compliance.completion_pct}%.")
        lines.append("Do not invent figures. Output only the summary.")
        return "\n".join(lines)
