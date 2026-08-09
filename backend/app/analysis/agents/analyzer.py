"""Analyzer agent: computes ratios and summarizes the financial position."""

from dataclasses import dataclass, field

from app.analysis.agents.base import Agent, AgentContext, AgentResult
from app.analysis.ratios import Ratio, RatioCalculator


@dataclass
class TrendSignal:
    metric: str
    current: float
    prior: float | None
    direction: str
    note: str
    chunk_id: str = ""


@dataclass
class AnalyzerData:
    ratios: list[Ratio]
    trends: list[TrendSignal]
    source_chunk_ids: list[str] = field(default_factory=list)


class AnalyzerAgent(Agent):
    """Focused solely on the numbers: ratios and year-over-year trends."""

    name = "analyzer"

    def run(self, context: AgentContext) -> AgentResult:
        if not context.financials or not context.ratios:
            return self.fail("No financial figures were extracted from the documents.")

        trends: list[TrendSignal] = []
        chunk_ids: set[str] = set()
        for metric, entries in context.financials.items.items():
            item = entries[0]
            chunk_ids.add(item.chunk_id)
            if item.prior_value is not None and item.prior_value != 0:
                delta = item.value - item.prior_value
                pct_change = round(delta / abs(item.prior_value) * 100, 1)
                direction = "up" if delta > 0 else "down"
                trends.append(TrendSignal(
                    metric=metric,
                    current=item.value,
                    prior=item.prior_value,
                    direction=direction,
                    note=f"{item.label} changed {pct_change}% year-over-year.",
                    chunk_id=item.chunk_id,
                ))
            else:
                trends.append(TrendSignal(
                    metric=metric,
                    current=item.value,
                    prior=item.prior_value,
                    direction="flat",
                    note=f"{item.label} reported with no prior-year comparison.",
                    chunk_id=item.chunk_id,
                ))

        for ratio in context.ratios:
            chunk_ids.update(ratio.source_chunk_ids)

        data = AnalyzerData(ratios=context.ratios, trends=trends, source_chunk_ids=sorted(chunk_ids))
        return AgentResult(agent=self.name, data=data, citations=data.source_chunk_ids)
