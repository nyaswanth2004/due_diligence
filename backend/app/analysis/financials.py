"""Deterministic extraction of key financial figures from document chunks.

Every figure keeps full provenance (source chunk, page, section, document) so
the due diligence report can point back to the exact evidence.
"""

import re
from dataclasses import dataclass, field

from app.models import Document, DocumentChunk

METRIC_LABELS: dict[str, str] = {
    "revenue": "Revenue",
    "gross_profit": "Gross Profit",
    "operating_income": "Operating Income",
    "net_income": "Net Income",
    "total_assets": "Total Assets",
    "current_assets": "Current Assets",
    "total_liabilities": "Total Liabilities",
    "current_liabilities": "Current Liabilities",
    "equity": "Shareholders' Equity",
    "inventory": "Inventory",
    "cash_from_operations": "Cash Flow from Operations",
    "cash_from_investing": "Cash Flow from Investing",
    "cash_from_financing": "Cash Flow from Financing",
}

_METRIC_PATTERNS: dict[str, list[re.Pattern]] = {
    "revenue": [
        re.compile(r"\btotal\s+revenue\b", re.I),
        re.compile(r"\bnet\s+revenue\b", re.I),
        re.compile(r"\btotal\s+sales\b", re.I),
        re.compile(r"\bnet\s+sales\b", re.I),
        re.compile(r"\brevenue\b", re.I),
    ],
    "gross_profit": [re.compile(r"\bgross\s+profit\b", re.I)],
    "operating_income": [
        re.compile(r"\boperating\s+income\b", re.I),
        re.compile(r"\boperating\s+profit\b", re.I),
    ],
    "net_income": [
        re.compile(r"\bnet\s+income\b", re.I),
        re.compile(r"\bnet\s+profit\b", re.I),
    ],
    "total_assets": [re.compile(r"\btotal\s+assets\b", re.I)],
    "current_assets": [re.compile(r"\bcurrent\s+assets\b", re.I)],
    "total_liabilities": [re.compile(r"\btotal\s+liabilities\b", re.I)],
    "current_liabilities": [re.compile(r"\bcurrent\s+liabilities\b", re.I)],
    "equity": [
        re.compile(r"\bshareholders['\u2019]?\s+equity\b", re.I),
        re.compile(r"\btotal\s+equity\b", re.I),
        re.compile(r"\bowners['\u2019]?\s+equity\b", re.I),
    ],
    "inventory": [re.compile(r"\binventory\b", re.I)],
    "cash_from_operations": [
        re.compile(r"\b(?:net\s+)?cash\s+(?:from|provided\s+by)\s+operating", re.I),
        re.compile(r"\boperating\s+activities\b", re.I),
    ],
    "cash_from_investing": [
        re.compile(r"\b(?:net\s+)?cash\s+(?:from|used\s+in)\s+investing", re.I),
        re.compile(r"\binvesting\s+activities\b", re.I),
    ],
    "cash_from_financing": [
        re.compile(r"\b(?:net\s+)?cash\s+(?:from|used\s+in)\s+financing", re.I),
        re.compile(r"\bfinancing\s+activities\b", re.I),
    ],
}

_NUM_RE = re.compile(r"\(?[-+]?\d[\d,]*(?:\.\d+)?\)?")
_YEAR_MIN, _YEAR_MAX = 1900, 2100


def _extract_numbers(line: str) -> list[float]:
    values: list[float] = []
    for match in _NUM_RE.finditer(line):
        token = match.group(0)
        negative = token.startswith("(") and token.endswith(")")
        try:
            value = float(token.strip("()").replace(",", ""))
        except ValueError:
            continue
        if _YEAR_MIN <= value <= _YEAR_MAX:
            continue
        if negative:
            value = -value
        values.append(value)
    return values


@dataclass
class FinancialItem:
    metric: str
    label: str
    value: float
    prior_value: float | None = None
    chunk_id: str = ""
    page: int = 0
    section: str = ""
    document_id: str = ""
    filename: str = ""


@dataclass
class FinancialData:
    items: dict[str, list[FinancialItem]] = field(default_factory=dict)

    def first(self, metric: str) -> FinancialItem | None:
        entries = self.items.get(metric)
        return entries[0] if entries else None

    def all(self, metric: str) -> list[FinancialItem]:
        return self.items.get(metric, [])

    def metrics(self) -> list[str]:
        return list(self.items)


class FinancialDataExtractor:
    """Scans chunks for known financial line items, keeping the first match
    per metric per document so cross-document scope is handled correctly."""

    def extract(self, chunks: list[DocumentChunk], documents: list[Document]) -> FinancialData:
        filename_of = {document.id: document.filename for document in documents}
        data = FinancialData()
        for chunk in chunks:
            for line in chunk.content.splitlines():
                line = line.strip()
                if not line:
                    continue
                for metric, patterns in _METRIC_PATTERNS.items():
                    if not any(pattern.search(line) for pattern in patterns):
                        continue
                    numbers = _extract_numbers(line)
                    if not numbers:
                        continue
                    metric_list = data.items.setdefault(metric, [])
                    existing_docs = {item.document_id for item in metric_list}
                    if chunk.document_id in existing_docs:
                        break
                    metric_list.append(
                        FinancialItem(
                            metric=metric,
                            label=METRIC_LABELS.get(metric, metric.replace("_", " ").title()),
                            value=numbers[0],
                            prior_value=numbers[1] if len(numbers) > 1 else None,
                            chunk_id=chunk.id,
                            page=chunk.page_number,
                            section=chunk.section,
                            document_id=chunk.document_id,
                            filename=filename_of.get(chunk.document_id, ""),
                        )
                    )
                    break
        return data
