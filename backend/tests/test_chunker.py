from app.ingestion.chunker import TextChunker
from app.ingestion.extractors.base import PageContent

DOC_ID = "test-doc"


def _pages(*texts: str):
    return [PageContent(page_number=i + 1, text=t) for i, t in enumerate(texts)]


def test_chunking_produces_provenance():
    text = "\n\n".join(f"Financial data paragraph number {i} with some numbers 1 2 3 4 5 6 7 8 9 0." for i in range(1, 40))
    chunks = TextChunker(chunk_size=200, overlap=20).chunk_pages(_pages(text), DOC_ID)

    assert len(chunks) >= 3
    for chunk in chunks:
        assert chunk["document_id"] == DOC_ID
        assert chunk["page_number"] >= 1
        assert "content" in chunk and chunk["content"]
        assert chunk["token_count"] >= 1
        assert chunk["chunk_index"] >= 0


def test_chunk_overlap_splits_long_blocks():
    long_block = "word " * 1000
    chunks = TextChunker(chunk_size=500, overlap=50).chunk_pages(_pages(long_block), DOC_ID)
    assert len(chunks) >= 3
    assert len(chunks[0]["content"]) <= 510


def test_section_tracking():
    text = "\n\n".join(
        [
            "1.1 Revenue\nTotal revenue grew 12% year over year.",
            "1.2 Expenses\nOperating expenses decreased by 5%.",
            "Notes to the financial statements\nThe company changed its depreciation policy.",
        ]
    )
    chunks = TextChunker(chunk_size=1000, overlap=0).chunk_pages(_pages(text), DOC_ID)
    assert chunks[0]["section"] == "1.1 Revenue"
    assert chunks[1]["section"] == "1.2 Expenses"
    assert chunks[2]["section"] == "Notes to the financial statements"


def test_empty_pages_produce_no_chunks():
    chunks = TextChunker().chunk_pages(_pages("   ", ""), DOC_ID)
    assert chunks == []
