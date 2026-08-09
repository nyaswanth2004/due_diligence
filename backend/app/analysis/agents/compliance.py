"""Compliance agent: checks disclosure coverage against a checklist."""

from dataclasses import dataclass, field

from app.analysis.agents.base import Agent, AgentContext, AgentResult
from app.analysis.ratios import RiskLevel

CHECKLIST: list[tuple[str, str]] = [
    ("revenue", "Revenue is disclosed."),
    ("gross_profit", "Gross profit is disclosed."),
    ("operating_income", "Operating income is disclosed."),
    ("net_income", "Net income is disclosed."),
    ("total_assets", "Total assets are disclosed."),
    ("total_liabilities", "Total liabilities are disclosed."),
    ("equity", "Shareholders' equity is disclosed."),
    ("cash_from_operations", "Cash flow from operations is disclosed."),
]


@dataclass
class ChecklistItem:
    item: str
    status: str  # "present" | "missing"
    note: str = ""


@dataclass
class ComplianceData:
    items: list[ChecklistItem]
    completion_pct: float = 0.0
    source_chunk_ids: list[str] = field(default_factory=list)


class ComplianceAgent(Agent):
    """Evaluates completeness of the financial disclosure."""

    name = "compliance"

    def run(self, context: AgentContext) -> AgentResult:
        financials = context.financials
        items: list[ChecklistItem] = []
        chunk_ids: set[str] = set()
        present = 0
        for metric, note in CHECKLIST:
            entry = financials.first(metric) if financials else None
            if entry:
                present += 1
                chunk_ids.add(entry.chunk_id)
                items.append(ChecklistItem(item=note, status="present"))
            else:
                items.append(ChecklistItem(item=note, status="missing", note="Not found in the provided documents."))

        completion = round(present / len(CHECKLIST) * 100, 1) if CHECKLIST else 0.0
        data = ComplianceData(items=items, completion_pct=completion, source_chunk_ids=sorted(chunk_ids))
        return AgentResult(agent=self.name, data=data, citations=data.source_chunk_ids)
