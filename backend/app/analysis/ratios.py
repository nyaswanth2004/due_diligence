"""Financial ratio calculation with deterministic interpretation."""

from dataclasses import dataclass, field
from typing import Literal

from app.analysis.financials import FinancialData

RiskLevel = Literal["low", "medium", "high", "info"]


@dataclass
class Ratio:
    name: str
    value: float
    formula: str
    interpretation: str
    risk_level: RiskLevel = "info"
    source_chunk_ids: list[str] = field(default_factory=list)


def _pct(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


class RatioCalculator:
    """Computes liquidity, solvency, and profitability ratios.

    A ratio is emitted only when both inputs were actually extracted from the
    documents — the report never invents inputs.
    """

    def calculate(self, financials: FinancialData) -> list[Ratio]:
        ratios: list[Ratio] = []
        add = ratios.append

        ca = financials.first("current_assets")
        cl = financials.first("current_liabilities")
        if ca and cl:
            value = _pct(ca.value, cl.value)
            level: RiskLevel = "high" if value < 1.0 else ("medium" if value < 1.5 else "low")
            add(Ratio(
                name="Current Ratio",
                value=round(value, 2),
                formula="Current Assets / Current Liabilities",
                interpretation=(
                    "Current assets do not cover current liabilities, indicating liquidity pressure."
                    if value < 1.0 else
                    "Current assets adequately cover current liabilities."
                ),
                risk_level=level,
                source_chunk_ids=[ca.chunk_id, cl.chunk_id],
            ))

        tl = financials.first("total_liabilities")
        equity = financials.first("equity")
        if tl and equity:
            value = _pct(tl.value, equity.value)
            level: RiskLevel = "high" if value > 2.0 else ("medium" if value > 1.0 else "low")
            add(Ratio(
                name="Debt-to-Equity",
                value=round(value, 2),
                formula="Total Liabilities / Shareholders' Equity",
                interpretation="High leverage relative to equity." if value > 2.0 else
                               "Leverage is within a moderate range.",
                risk_level=level,
                source_chunk_ids=[tl.chunk_id, equity.chunk_id],
            ))

        ta = financials.first("total_assets")
        if tl and ta:
            value = _pct(tl.value, ta.value)
            level: RiskLevel = "high" if value > 0.8 else ("medium" if value > 0.6 else "low")
            add(Ratio(
                name="Debt Ratio",
                value=round(value, 2),
                formula="Total Liabilities / Total Assets",
                interpretation="Assets are heavily financed by debt." if value > 0.8 else
                               "Debt financing is within acceptable levels.",
                risk_level=level,
                source_chunk_ids=[tl.chunk_id, ta.chunk_id],
            ))

        ni = financials.first("net_income")
        revenue = financials.first("revenue")
        if ni and revenue:
            value = _pct(ni.value, revenue.value)
            level: RiskLevel = "high" if value < 0 else ("low" if value > 0.10 else "medium")
            add(Ratio(
                name="Net Profit Margin",
                value=round(value, 4),
                formula="Net Income / Revenue",
                interpretation="Operations are loss-making." if value < 0 else
                               "Operations convert revenue into profit.",
                risk_level=level,
                source_chunk_ids=[ni.chunk_id, revenue.chunk_id],
            ))

        if ni and ta:
            value = _pct(ni.value, ta.value)
            add(Ratio(
                name="Return on Assets",
                value=round(value, 4),
                formula="Net Income / Total Assets",
                interpretation="Profitability relative to the asset base.",
                risk_level="low" if value > 0 else "high",
                source_chunk_ids=[ni.chunk_id, ta.chunk_id],
            ))

        if ni and equity:
            value = _pct(ni.value, equity.value)
            add(Ratio(
                name="Return on Equity",
                value=round(value, 4),
                formula="Net Income / Shareholders' Equity",
                interpretation="Return generated on shareholders' equity.",
                risk_level="low" if value > 0 else "high",
                source_chunk_ids=[ni.chunk_id, equity.chunk_id],
            ))

        return ratios
