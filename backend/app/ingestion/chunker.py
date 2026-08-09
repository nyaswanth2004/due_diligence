import re

from app.core.config import settings
from app.ingestion.extractors.base import PageContent

_HEADING_RE = re.compile(r"^(section\s+\d+|appendix\s+[a-z]|\d+(\.\d+)*[.)]?\s)", re.IGNORECASE)

_HEADING_KEYWORDS = (
    "notes to the financial statements",
    "balance sheet",
    "income statement",
    "statement of cash flows",
    "statement of profit or loss",
    "statement of changes in equity",
    "statement of financial position",
    "audit report",
    "independent auditor",
    "directors' report",
    "directors report",
    "management discussion",
    "corporate governance",
    "financial statements",
    "summary of significant accounting policies",
    "segment information",
    "related party",
    "commitments and contingencies",
)


def _is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 80:
        return False
    if line.endswith(tuple(".:!?,")):
        return False
    if _HEADING_RE.match(line):
        return True
    if any(kw in line.lower() for kw in _HEADING_KEYWORDS):
        return True
    if line.isupper() and len(line) <= 60:
        return True
    return False


def _split_blocks(page_text: str) -> list[str]:
    blocks = [b.strip() for b in page_text.split("\n\n") if b.strip()]
    return blocks


class TextChunker:
    """Splits extracted pages into overlapping, provenance-tracked chunks.

    Each chunk records the source page, the nearest section heading, and an
    approximate token count so downstream retrieval can cite exact locations.
    """

    def __init__(self, chunk_size: int | None = None, overlap: int | None = None) -> None:
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.overlap = overlap if overlap is not None else settings.CHUNK_OVERLAP

    def chunk_pages(self, pages: list[PageContent], document_id: str) -> list[dict]:
        chunks: list[dict] = []
        buffer = ""
        buffer_page = 0
        buffer_section = ""
        current_section = ""

        def flush() -> None:
            nonlocal buffer
            if buffer.strip():
                chunks.append(self._make_chunk(document_id, len(chunks), buffer_page,
                                               buffer_section, buffer))
            buffer = ""

        def add(block: str, page_number: int) -> None:
            nonlocal buffer, buffer_page, buffer_section, current_section
            if not buffer:
                buffer_page = page_number
                buffer_section = current_section
            if len(buffer) + len(block) + 2 <= self.chunk_size:
                buffer += block if not buffer else f"\n\n{block}"
                return
            flush()
            if len(block) > self.chunk_size:
                for part in self._hard_split(block):
                    chunks.append(
                        self._make_chunk(document_id, len(chunks), page_number,
                                         current_section, part)
                    )
            else:
                buffer = block
                buffer_page = page_number
                buffer_section = current_section

        for page in pages:
            for block in _split_blocks(page.text):
                lines = block.split("\n")
                first_line = lines[0].strip()
                if _is_heading(first_line):
                    flush()
                    current_section = first_line
                    rest = "\n".join(lines[1:]).strip()
                    if rest:
                        add(rest, page.page_number)
                    continue
                add(block, page.page_number)

        flush()
        return chunks

    def _hard_split(self, text: str) -> list[str]:
        parts: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            if end < len(text):
                cut = text.rfind(" ", start + int(self.chunk_size * 0.6), end)
                if cut > start:
                    end = cut
            parts.append(text[start:end].strip())
            if end >= len(text):
                break
            start = end - self.overlap
        return parts

    @staticmethod
    def _make_chunk(document_id: str, index: int, page: int, section: str, content: str) -> dict:
        return {
            "document_id": document_id,
            "chunk_index": index,
            "page_number": page,
            "section": section,
            "content": content,
            "token_count": max(1, len(content) // 4),
        }
