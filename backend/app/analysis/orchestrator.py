"""Orchestrates the multi-agent due diligence workflow.

Runs the deterministic extraction pipeline (figures -> ratios), then the three
analysis agents, and finally the report agent. Agent outputs are stashed on the
context so downstream agents can consume them without coupling.
"""

from dataclasses import dataclass, field
from typing import Any

from app.analysis.agents.analyzer import AnalyzerAgent, AnalyzerData
from app.analysis.agents.base import AgentContext, AgentResult
from app.analysis.agents.compliance import ComplianceAgent, ComplianceData
from app.analysis.agents.report import ReportAgent, ReportData
from app.analysis.agents.risk import RiskAgent, RiskData
from app.analysis.financials import FinancialData, FinancialDataExtractor
from app.analysis.ratios import Ratio, RatioCalculator
from app.models import Document, DocumentChunk


@dataclass
class WorkflowResult:
    financials: FinancialData
    ratios: list[Ratio]
    analyzer: AgentResult
    risk: AgentResult
    compliance: AgentResult
    report: AgentResult
    agent_outputs: list[AgentResult] = field(default_factory=list)

    @property
    def report_data(self) -> ReportData | None:
        return self.report.data if isinstance(self.report.data, ReportData) else None


class DueDiligenceOrchestrator:
    def __init__(self, llm: Any | None = None):
        self._extractor = FinancialDataExtractor()
        self._ratios = RatioCalculator()
        self._agents = [
            AnalyzerAgent(),
            RiskAgent(),
            ComplianceAgent(),
        ]
        self._report_agent = ReportAgent(llm=llm)

    def run(self, documents: list[Document], chunks: list[DocumentChunk]) -> WorkflowResult:
        financials = self._extractor.extract(chunks, documents)
        ratios = self._ratios.calculate(financials)

        context = AgentContext(
            documents=documents,
            chunks=chunks,
            financials=financials,
            ratios=ratios,
        )

        outputs: list[AgentResult] = []
        for agent in self._agents:
            result = agent.run(context)
            outputs.append(result)
            if isinstance(result.data, AnalyzerData):
                context.analysis = result.data
            elif isinstance(result.data, RiskData):
                context.risk = result.data
            elif isinstance(result.data, ComplianceData):
                context.compliance = result.data

        report = self._report_agent.run(context)
        outputs.append(report)

        return WorkflowResult(
            financials=financials,
            ratios=ratios,
            analyzer=outputs[0],
            risk=outputs[1],
            compliance=outputs[2],
            report=report,
            agent_outputs=outputs,
        )
