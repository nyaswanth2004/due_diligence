from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app.analysis.financials import FinancialData
from app.analysis.ratios import Ratio
from app.models import Document, DocumentChunk

if TYPE_CHECKING:
    from app.analysis.agents.analyzer import AnalyzerData
    from app.analysis.agents.compliance import ComplianceData
    from app.analysis.agents.risk import RiskData


@dataclass
class AgentContext:
    documents: list[Document]
    chunks: list[DocumentChunk]
    financials: FinancialData | None = None
    ratios: list[Ratio] | None = None
    analysis: AnalyzerData | None = None
    risk: RiskData | None = None
    compliance: ComplianceData | None = None


@dataclass
class AgentResult:
    agent: str
    data: Any = None
    citations: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None


class Agent(ABC):
    """A specialized analysis step in the due diligence workflow."""

    name: str = "agent"

    @abstractmethod
    def run(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError

    def fail(self, error: str) -> AgentResult:
        return AgentResult(agent=self.name, success=False, error=error)
