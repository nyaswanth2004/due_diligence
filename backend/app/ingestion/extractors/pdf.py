import io

import pdfplumber

from app.ingestion.extractors.base import BaseExtractor, ExtractionResult, PageContent

MIN_TEXT_CHARS_FOR_TEXT_BASED = 40


def _format_table(rows: list[list[str | None]]) -> str:
    lines = []
    for row in rows:
        cells = [str(c).strip() if c is not None else "" for c in row]
        cleaned = [c for c in cells if c]
        if cleaned:
            lines.append(" | ".join(cleaned))
    return "\n".join(lines)


class PdfExtractor(BaseExtractor):
    """Extracts text (and table content) from PDF pages.

    A PDF is flagged as `scanned` when it yields almost no extractable text,
    signalling the pipeline to run OCR on it.
    """

    def extract(self, content: bytes, filename: str) -> ExtractionResult:
        pages: list[PageContent] = []
        total_chars = 0
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                for table in tables:
                    table_text = _format_table(table)
                    if table_text:
                        text = f"{text}\n\n[TABLE]\n{table_text}\n[/TABLE]" if text else (
                            f"[TABLE]\n{table_text}\n[/TABLE]"
                        )
                total_chars += len(text)
                pages.append(PageContent(page_number=index, text=text.strip()))

        scanned = total_chars < MIN_TEXT_CHARS_FOR_TEXT_BASED and len(pages) > 0
        return ExtractionResult(
            pages=pages,
            metadata={"scanned": scanned, "page_count": len(pages)},
        )
