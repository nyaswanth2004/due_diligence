"""Generate realistic sample financial documents for testing VeritasIQ.

Creates a full set of cross-referenced financial documents for a fictional
company (ACME Manufacturing Inc.) with deliberate red flags so you can exercise
the document ingestion, hybrid retrieval, grounded Q&A, and the due-diligence
report pipeline (financial extraction + ratios + risk/compliance agents).

The figures are consistent across documents and use the same magnitude
(thousands) so deterministic ratio extraction yields sensible results.

Run (from backend/):
    .venv\\Scripts\\python -m scripts.generate_sample_data

Output:  sample_data/  (one directory up from backend/)
  ├── acme_fy24_annual_report.pdf
  ├── acme_fy24_balance_sheet.pdf
  ├── acme_fy24_income_statement.pdf
  ├── acme_fy24_cash_flow.pdf
  ├── acme_fy24_audit_report.pdf
  ├── acme_fy24_income_statement.xlsx
  └── acme_fy24_cash_flow.csv
"""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "sample_data"

PAGE_W, PAGE_H = landscape(A4)  # 842 x 595
LINE_H = 13
MARGIN = 40


def _new_page(c: canvas.Canvas, title: str, subtitle: str = "") -> None:
    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN, PAGE_H - MARGIN, title)
    if subtitle:
        c.setFont("Helvetica", 10)
        c.drawString(MARGIN, PAGE_H - MARGIN - 18, subtitle)
    c.setFont("Helvetica", 9)


def _footer(c: canvas.Canvas, page_no: int) -> None:
    c.setFont("Helvetica", 7)
    c.drawCentredString(
        PAGE_W / 2,
        18,
        "ACME Manufacturing Inc. | Confidential - For Testing Only | Page %d" % page_no,
    )


def _body(c: canvas.Canvas, lines: list[str]) -> int:
    """Draw lines with basic (bold/label) formatting, returns next y."""
    y = PAGE_H - MARGIN - 32
    for line in lines:
        if y < 30:
            _new_page(c, "")
            _footer(c, c.getPageNumber())
            y = PAGE_H - MARGIN - 32
        if line.startswith("##"):
            c.setFont("Helvetica-Bold", 11)
            c.drawString(MARGIN, y, line.lstrip("#").strip())
        else:
            c.setFont("Courier-Bold" if line.startswith("  ") and len(line) > 40 else "Helvetica", 9)
            c.drawString(MARGIN + (18 if line.startswith("  ") else 0), y, line)
        y -= LINE_H
    return y


def _write_pdf(filename: str, pages: list[tuple[str, str, list[str]]]) -> None:
    path = OUTPUT_DIR / filename
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    _new_page(c, pages[0][0], pages[0][1])
    _footer(c, 1)
    _body(c, pages[0][2])
    for i, (title, subtitle, lines) in enumerate(pages[1:], start=2):
        _new_page(c, title, subtitle)
        _footer(c, i)
        _body(c, lines)
    c.save()
    print(f"  created: {path.name} ({path.stat().st_size} bytes)")


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------

def annual_report() -> None:
    pages = [
        (
            "ACME Manufacturing Inc. - Annual Report FY2024",
            "Fiscal year ended December 31, 2024",
            [
                "## Chairman's Statement",
                "Dear Shareholders,",
                "",
                "Fiscal year 2024 was a transformative year for ACME Manufacturing.",
                "Top-line growth reached 15.4% as we expanded into European markets and",
                "launched our new automation product line.",
                "",
                "We must be transparent about the challenges we face. Rising input costs,",
                "supply chain disruptions, and the cost of our strategic acquisitions have",
                "increased our leverage. Management has implemented a cost reduction program",
                "targeting $40 million in annual savings.",
                "",
                "We remain confident in our long-term strategy and the strength of our",
                "product portfolio.",
            ],
        ),
        (
            "ACME Manufacturing Inc. - Annual Report FY2024",
            "Fiscal year ended December 31, 2024",
            [
                "## Financial Highlights (in thousands)",
                "Revenue: 485,200 (FY2023: 420,500, FY2022: 365,100)",
                "Gross Profit: 169,800 (FY2023: 158,500, FY2022: 142,400)",
                "Operating Income: 54,200 (FY2023: 58,900, FY2022: 55,800)",
                "Net Income: 26,800 (FY2023: 37,900, FY2022: 38,400)",
                "EBITDA: 78,500 (FY2023: 74,200, FY2022: 68,900)",
                "",
                "## Key Ratios",
                "Current Ratio: 1.1x (industry average: 2.0x)",
                "Debt-to-Equity: 2.1x (FY2022: 1.2x)",
                "Net Profit Margin: 8.0% (FY2022: 11.0%)",
                "Return on Equity: 11.2% (FY2022: 16.8%)",
                "Interest Coverage: 2.4x (FY2022: 5.1x)",
            ],
        ),
        (
            "ACME Manufacturing Inc. - Annual Report FY2024",
            "Balance Sheet Summary (in thousands)",
            [
                "## Balance Sheet Summary",
                "Total Assets: 659,300",
                "Cash and Cash Equivalents: 22,100",
                "Accounts Receivable: 98,500",
                "Inventory: 85,300",
                "Property, Plant & Equipment: 310,200",
                "Intangible Assets: 96,300",
                "",
                "Total Liabilities: 464,800",
                "Accounts Payable: 61,200",
                "Short-term Debt: 85,000",
                "Long-term Debt: 245,500",
                "Total Shareholders Equity: 194,500",
            ],
        ),
        (
            "ACME Manufacturing Inc. - Annual Report FY2024",
            "Income Statement (in thousands)",
            [
                "## Consolidated Income Statement",
                "Revenue: 485,200",
                "Cost of Goods Sold: 315,400",
                "Gross Profit: 169,800",
                "",
                "Operating Expenses:",
                "  Selling, General & Admin: 89,600",
                "  Research & Development: 26,000",
                "Total Operating Expenses: 115,600",
                "",
                "Operating Income: 54,200",
                "Interest Expense: 18,500",
                "Income Before Taxes: 35,700",
                "Income Tax Expense: 8,900",
                "Net Income: 26,800",
                "",
                "EPS (Basic): 2.68",
                "EPS (Diluted): 2.61",
            ],
        ),
        (
            "ACME Manufacturing Inc. - Annual Report FY2024",
            "Cash Flow Statement (in thousands)",
            [
                "## Consolidated Statement of Cash Flows",
                "Cash Flow from Operating Activities:",
                "  Net Income: 26,800",
                "  Depreciation & Amortization: 24,300",
                "  Changes in Working Capital: (31,500)",
                "  Net Cash from Operating Activities: 19,600",
                "",
                "Cash Flow from Investing Activities:",
                "  Capital Expenditures: (48,200)",
                "  Acquisition of Subsidiaries: (72,000)",
                "  Net Cash from Investing Activities: (120,200)",
                "",
                "Cash Flow from Financing Activities:",
                "  Proceeds from Debt: 95,000",
                "  Dividend Payments: (8,400)",
                "  Net Cash from Financing Activities: 86,600",
                "",
                "Net Change in Cash: (14,000)",
                "Beginning Cash Balance: 36,100",
                "Ending Cash Balance: 22,100",
            ],
        ),
        (
            "ACME Manufacturing Inc. - Annual Report FY2024",
            "Related Party Transactions",
            [
                "## Related Party Transactions",
                "The Company entered into the following transactions with related parties",
                "during FY2024:",
                "",
                "1. ACME Holdings Ltd. (parent company, 51% ownership) - Management",
                "   services agreement totaling $3.2 million.",
                "",
                "2. ACME Properties LLC (controlled by the Chief Executive Officer) -",
                "   Lease payments totaling $4.8 million for the Company's corporate",
                "   headquarters. This agreement was not subject to independent valuation.",
                "",
                "3. Redwood Supply Co. (owned by a board member) - Raw material purchases",
                "   of $12.5 million, representing 8% of total raw material purchases.",
                "",
                "Management believes these transactions were conducted at arm's length.",
            ],
        ),
        (
            "ACME Manufacturing Inc. - Annual Report FY2024",
            "Subsequent Events",
            [
                "## Subsequent Events",
                "On June 15, 2025, subsequent to the fiscal year end, the Company received",
                "a notice from its primary lender indicating potential covenant violations",
                "related to its debt-to-EBITDA ratio.",
                "",
                "The Company is in discussions with the lender to negotiate a waiver.",
                "If a waiver is not obtained, the Company's $85 million short-term debt",
                "facility could become due on demand, raising the risk of default.",
                "",
                "A related dispute is pending before the commercial court relating to a",
                "supplier contract; legal counsel has assessed a contingent liability of",
                "up to $6 million.",
            ],
        ),
    ]
    _write_pdf("acme_fy24_annual_report.pdf", pages)


def balance_sheet() -> None:
    pages = [
        (
            "ACME Manufacturing Inc. - Consolidated Balance Sheet",
            "As at December 31 (in thousands)",
            [
                "## Assets",
                "Current Assets: 218,300",
                "  Cash and Cash Equivalents: 22,100",
                "  Accounts Receivable: 98,500",
                "  Inventory: 85,300",
                "  Prepaid Expenses: 12,400",
                "Non-Current Assets: 441,000",
                "  Property, Plant & Equipment: 310,200",
                "  Intangible Assets: 96,300",
                "  Goodwill: 24,500",
                "Total Assets: 659,300",
                "",
                "## Liabilities and Equity",
                "Current Liabilities: 198,700",
                "  Accounts Payable: 61,200",
                "  Short-term Debt: 85,000",
                "  Accrued Liabilities: 52,500",
                "Non-Current Liabilities: 266,100",
                "  Long-term Debt: 245,500",
                "  Deferred Tax Liabilities: 20,600",
                "Total Liabilities: 464,800",
                "",
                "Shareholders' Equity:",
                "  Common Stock: 50,000",
                "  Retained Earnings: 144,500",
                "Total Equity: 194,500",
                "Total Liabilities and Equity: 659,300",
            ],
        ),
    ]
    _write_pdf("acme_fy24_balance_sheet.pdf", pages)


def income_statement() -> None:
    pages = [
        (
            "ACME Manufacturing Inc. - Consolidated Income Statement",
            "For the years ended December 31 (in thousands)",
            [
                "## Income Statement",
                "Revenue: 485,200      420,500      365,100",
                "Cost of Goods Sold: 315,400      262,000      222,700",
                "Gross Profit: 169,800      158,500      142,400",
                "",
                "Operating Expenses:",
                "  Selling, General & Admin: 89,600",
                "  Research & Development: 26,000",
                "Total Operating Expenses: 115,600",
                "",
                "Operating Income: 54,200       58,900       55,800",
                "Interest Expense: 18,500       11,600        7,400",
                "Other Income (Expense): 4,500      3,200      2,800",
                "Income Before Taxes: 35,700      50,500      51,200",
                "Income Tax Expense: 8,900       12,600      12,800",
                "Net Income: 26,800       37,900      38,400",
                "",
                "Shares Outstanding: 10,000,000",
                "EPS (Basic): 2.68",
            ],
        ),
    ]
    _write_pdf("acme_fy24_income_statement.pdf", pages)


def cash_flow() -> None:
    pages = [
        (
            "ACME Manufacturing Inc. - Consolidated Statement of Cash Flows",
            "For the years ended December 31 (in thousands)",
            [
                "## Operating Activities",
                "Net Income: 26,800       37,900      38,400",
                "Depreciation & Amortization: 24,300      20,100      17,200",
                "Changes in Working Capital:",
                "  Accounts Receivable: (16,200)",
                "  Inventories: (12,500)",
                "  Accounts Payable: 8,800",
                "  Accrued Liabilities: 10,700",
                "Other Adjustments: (21,500)",
                "Net Cash from Operating Activities: 19,600      54,200      51,000",
                "",
                "## Investing Activities",
                "Capital Expenditures: (48,200)",
                "Acquisition of Subsidiaries: (72,000)",
                "Purchase of Intangibles: (38,100)",
                "Other Investing: 2,100",
                "Net Cash from Investing Activities: (156,200)",
                "",
                "## Financing Activities",
                "Proceeds from Long-term Debt: 95,000",
                "Repayment of Short-term Debt: (7,600)",
                "Dividend Payments: (8,400)",
                "Other Financing: (3,900)",
                "Net Cash from Financing Activities: 75,100",
                "",
                "Net Change in Cash: (61,500)",
                "Cash, beginning of year: 83,600",
                "Cash, end of year: 22,100",
            ],
        ),
    ]
    _write_pdf("acme_fy24_cash_flow.pdf", pages)


def audit_report() -> None:
    pages = [
        (
            "ACME Manufacturing Inc. - Independent Auditor's Report",
            "For the year ended December 31, 2024",
            [
                "To the Shareholders and Board of Directors of ACME Manufacturing Inc.",
                "",
                "## Opinion",
                "We have audited the consolidated financial statements of ACME Manufacturing",
                "Inc., which comprise the consolidated balance sheet as at December 31, 2024,",
                "and the consolidated statement of income, statement of changes in equity,",
                "and statement of cash flows for the year then ended, and notes to the",
                "financial statements.",
                "",
                "In our opinion, except for the effects of the matter described in the Basis",
                "for Qualified Opinion section, the consolidated financial statements present",
                "fairly, in all material respects, the financial position of the Company.",
                "",
                "## Basis for Qualified Opinion",
                "As described in Note 6 to the financial statements, the Company entered into",
                "lease agreements with ACME Properties LLC, an entity controlled by the Chief",
                "Executive Officer. The Company recorded lease payments of $4.8 million to",
                "this related party during the year. The terms of these agreements were not",
                "subject to independent valuation, and we were unable to determine whether",
                "the lease payments were made at arm's length.",
            ],
        ),
        (
            "ACME Manufacturing Inc. - Independent Auditor's Report",
            "Key Audit Matters",
            [
                "## Key Audit Matters",
                "### Revenue Recognition",
                "The Company recognized revenue of $485.2 million in FY2024. The timing of",
                "revenue recognition is a key audit matter due to the complexity of the",
                "Company's multi-element software and hardware arrangements.",
                "",
                "We tested a sample of revenue transactions, reviewed the Company's revenue",
                "recognition policies against ASC 606, and obtained management representations.",
                "",
                "### Valuation of Intangible Assets",
                "The Company acquired two subsidiaries during FY2024 for total consideration",
                "of $72 million, recording $38.1 million of intangible assets.",
                "",
                "### Internal Controls",
                "We identified a material weakness in the Company's internal control over",
                "financial reporting relating to the period-end cutoff of vendor invoices.",
                "Management has not yet remediated this material weakness as of the report date.",
            ],
        ),
        (
            "ACME Manufacturing Inc. - Independent Auditor's Report",
            "Going Concern",
            [
                "## Substantial Doubt About the Company's Ability to Continue as a Going Concern",
                "",
                "The accompanying consolidated financial statements have been prepared assuming",
                "the Company will continue as a going concern.",
                "",
                "As discussed in Note 2.1 to the financial statements, the Company's cash flows",
                "from operations have declined from $51.0 million in FY2022 to $19.6 million in",
                "FY2024. The Company's current ratio of 1.1x is below the industry average of",
                "2.0x, and its debt-to-equity ratio has risen to 2.1x.",
                "",
                "Additionally, on June 15, 2025, subsequent to year-end, the Company received",
                "notice of potential covenant violations from its primary lender. These matters,",
                "along with the fact that $85 million of short-term debt matures within 12 months",
                "while the Company has only $22.1 million in cash, raise substantial doubt about",
                "the Company's ability to continue as a going concern.",
                "",
                "This constitutes a going concern qualification. The financial statements do not",
                "include any adjustments that might result from the outcome of this uncertainty.",
            ],
        ),
        (
            "ACME Manufacturing Inc. - Independent Auditor's Report",
            "Critical Accounting Estimates & Litigation",
            [
                "## Critical Accounting Estimates",
                "### Inventory Valuation",
                "The Company maintains inventory of $85.3 million. Due to rapid technological",
                "obsolescence, the Company recorded an inventory write-down of $6.2 million in",
                "FY2024. The determination of net realizable value involves significant",
                "management judgment.",
                "",
                "### Allowance for Doubtful Accounts",
                "Accounts receivable balance of $98.5 million. The Company's allowance for",
                "doubtful accounts was reduced from 3.2% in FY2023 to 2.1% in FY2024 despite",
                "an increase in accounts receivable aging over 90 days from 8% to 14%.",
                "",
                "## Pending Litigation",
                "The Company is party to litigation with a former supplier relating to an",
                "alleged breach of a supply agreement. The Company disputes the claim and has",
                "recorded a contingent liability of up to $6 million. Legal counsel believes",
                "the range of possible loss is between $2 million and $6 million.",
            ],
        ),
    ]
    _write_pdf("acme_fy24_audit_report.pdf", pages)


def income_statement_xlsx() -> None:
    """Spreadsheet version of the income statement (tests the XLSX extractor)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Income Statement"
    ws.append(["ACME Manufacturing Inc. - Income Statement"])
    ws.append(["For the years ended December 31 (in thousands)"])
    ws.append([])
    ws.append(["Item", "2024", "2023", "2022"])
    rows = [
        ("Revenue", 485200, 420500, 365100),
        ("Cost of Goods Sold", 315400, 262000, 222700),
        ("Gross Profit", 169800, 158500, 142400),
        ("Operating Income", 54200, 58900, 55800),
        ("Net Income", 26800, 37900, 38400),
        ("Total Assets", 659300, 557000, 472400),
        ("Total Liabilities", 464800, 333300, 248000),
        ("Total Equity", 194500, 223700, 224400),
        ("Cash from Operating Activities", 19600, 54200, 51000),
    ]
    for row in rows:
        ws.append(list(row))
    path = OUTPUT_DIR / "acme_fy24_income_statement.xlsx"
    wb.save(path)
    print(f"  created: {path.name} ({path.stat().st_size} bytes)")


def cash_flow_csv() -> None:
    """CSV version of the cash flow statement (tests the CSV extractor)."""
    path = OUTPUT_DIR / "acme_fy24_cash_flow.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ACME Manufacturing Inc. - Statement of Cash Flows"])
        writer.writerow(["For the years ended December 31 (in thousands)"])
        writer.writerow([])
        writer.writerow(["Item", "2024", "2023", "2022"])
        rows = [
            ("Net Income", 26800, 37900, 38400),
            ("Operating Activities", 19600, 54200, 51000),
            ("Investing Activities", -156200, -56000, -44800),
            ("Financing Activities", 75100, 38100, 5500),
            ("Net Change in Cash", -61500, 36300, 11700),
            ("Cash, end of year", 22100, 83600, 47300),
        ]
        for row in rows:
            writer.writerow(list(row))
    print(f"  created: {path.name} ({path.stat().st_size} bytes)")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating sample documents in: {OUTPUT_DIR}\n")
    annual_report()
    balance_sheet()
    income_statement()
    cash_flow()
    audit_report()
    income_statement_xlsx()
    cash_flow_csv()
    print("\nDone. 7 sample files generated.\n")
    print("Suggested test flow:")
    print("  1. Start the backend:  uvicorn app.main:app --reload")
    print("  2. Create an admin user (see README) and login to get a JWT.")
    print("  3. Upload the sample documents via POST /api/v1/documents")
    print("  4. Run GET /api/v1/search?q=... to exercise hybrid retrieval")
    print("  5. POST /api/v1/qa with a question to test grounded Q&A")
    print("  6. POST /api/v1/reports/generate to produce a due-diligence report")


if __name__ == "__main__":
    main()
