import re

DOC_TYPES = [
    "annual_report",
    "balance_sheet",
    "income_statement",
    "cash_flow_statement",
    "audit_report",
    "tax_filing",
    "compliance_document",
    "governance_report",
    "financial_statements",
]

UNKNOWN_TYPE = "unknown"

SIGNATURES: dict[str, list[str]] = {
    "annual_report": [
        "annual report",
        "annual financial report",
        "chairman",
        "chairperson",
        "board of directors",
        "company overview",
        "business overview",
        "management discussion",
        "notes to the financial statements",
    ],
    "balance_sheet": [
        "balance sheet",
        "statement of financial position",
        "current assets",
        "non-current assets",
        "current liabilities",
        "non-current liabilities",
        "shareholders' equity",
        "shareholders equity",
        "total assets",
        "total liabilities",
    ],
    "income_statement": [
        "income statement",
        "profit and loss",
        "statement of operations",
        "statement of profit or loss",
        "total revenue",
        "gross profit",
        "operating income",
        "net income",
        "earnings before",
    ],
    "cash_flow_statement": [
        "cash flow statement",
        "statement of cash flows",
        "cash flows",
        "operating activities",
        "investing activities",
        "financing activities",
        "net cash",
    ],
    "audit_report": [
        "audit report",
        "independent auditor",
        "independent auditors",
        "auditor's opinion",
        "auditor’s opinion",
        "opinion",
        "material misstatement",
        "auditor's responsibility",
        "auditor’s responsibility",
        "we have audited",
    ],
    "tax_filing": [
        "tax return",
        "income tax return",
        "taxable income",
        "internal revenue",
        "tax filing",
        "taxpayer",
        "form 10-k",  # regulatory filing with tax content
        "deferred tax",
    ],
    "compliance_document": [
        "compliance",
        "regulatory",
        "regulation",
        "whistleblower",
        "anti-money laundering",
        "aml",
        "know your customer",
        "kyc",
        "code of conduct",
        "policy statement",
    ],
    "governance_report": [
        "corporate governance",
        "governance report",
        "remuneration",
        "risk management",
        "board composition",
        "audit committee",
        "nomination committee",
        "stakeholder",
    ],
    "financial_statements": [
        "financial statements",
        "consolidated financial",
        "statement of financial",
        "for the year ended",
        "for the years ended",
    ],
}

FILENAME_SIGNATURES: dict[str, list[str]] = {
    "annual_report": ["annual-report", "annualreport", "annual_report"],
    "balance_sheet": ["balance-sheet", "balancesheet", "balance_sheet"],
    "income_statement": [
        "income-statement",
        "incomestatement",
        "income_statement",
        "profit-and-loss",
        "profitandloss",
        "p&l",
        "pl-statement",
    ],
    "cash_flow_statement": [
        "cash-flow",
        "cashflow",
        "cash_flow",
        "statement-of-cash",
    ],
    "audit_report": ["audit-report", "auditreport", "audit_report"],
    "tax_filing": ["tax-return", "taxreturn", "tax_filing", "tax-"],
    "compliance_document": ["compliance", "kyc", "aml-"],
    "governance_report": ["governance"],
}

_FILENAME_TEMPLATE = re.compile(r"[^a-z0-9]+")


def _normalize(text: str) -> str:
    return _FILENAME_TEMPLATE.sub("-", text.lower().strip("-"))


class DocumentClassifier:
    """Heuristic, explainable document-type classifier.

    Uses weighted keyword scoring against the document's own text; filename
    signals are used first because filenames are highly discriminative
    (e.g. "BalanceSheet_FY2024.xlsx").
    """

    def classify(self, filename: str, text: str) -> tuple[str, float]:
        name_score = self._classify_by_filename(filename)
        if name_score[0] != UNKNOWN_TYPE and name_score[1] >= 0.5:
            return name_score

        content_score = self._classify_by_content(text)
        if content_score[0] != UNKNOWN_TYPE and content_score[1] >= 0.15:
            return content_score

        if name_score[0] != UNKNOWN_TYPE:
            return name_score
        return content_score if content_score[0] != UNKNOWN_TYPE else (UNKNOWN_TYPE, 0.0)

    def _classify_by_filename(self, filename: str) -> tuple[str, float]:
        norm = _normalize(filename)
        best_type, best_score = UNKNOWN_TYPE, 0.0
        for doc_type, patterns in FILENAME_SIGNATURES.items():
            for pattern in patterns:
                if pattern in norm:
                    score = 1.0 if pattern.endswith("-") else 0.9
                    if score > best_score:
                        best_type, best_score = doc_type, score
        return best_type, best_score

    def _classify_by_content(self, text: str) -> tuple[str, float]:
        lowered = text.lower()
        scores: dict[str, int] = {}
        for doc_type, keywords in SIGNATURES.items():
            count = sum(1 for kw in keywords if kw in lowered)
            if count:
                scores[doc_type] = count

        if not scores:
            return UNKNOWN_TYPE, 0.0

        best_type = max(scores, key=scores.get)
        total = sum(scores.values())
        best = scores[best_type]
        return best_type, best / max(total, 1)
