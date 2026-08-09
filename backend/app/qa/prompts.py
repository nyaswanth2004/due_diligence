from app.core.config import settings
from app.schemas.qa import EvidenceChunk, QAMessage

SYSTEM_PROMPT = (
    "You are VeritasIQ, a senior financial due diligence analyst assistant.\n"
    "Answer the user's question using ONLY the document excerpts provided below.\n"
    "Rules:\n"
    "- Base every factual claim on the excerpts. Never invent figures, dates, or statements.\n"
    "- For each claim, include in the \"citations\" array the exact chunk id(s) that support it.\n"
    "- If the excerpts do not contain enough information to answer, state that clearly and "
    "return an empty citations array.\n"
    "- Do not add analysis beyond what the excerpts support.\n"
    "- Respond ONLY with valid JSON matching this schema: "
    "{\"answer\": \"...\", \"citations\": [\"chunk_id\", ...]}"
)


def format_context(chunks: list[EvidenceChunk]) -> str:
    lines: list[str] = []
    for chunk in chunks:
        header = (
            f"[[{chunk.chunk_id}]] file={chunk.filename!r} type={chunk.doc_type!r} "
            f"page={chunk.page_number} section={chunk.section!r}"
        )
        lines.append(header)
        lines.append(chunk.content)
        lines.append("")
    return "\n".join(lines).strip()


def build_messages(
    chunks: list[EvidenceChunk],
    question: str,
    history: list[QAMessage] | None = None,
) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for message in history[-settings.QA_MAX_HISTORY:]:
            messages.append({"role": message.role, "content": message.content})

    context_block = format_context(chunks)
    user_content = (
        f"DOCUMENT EXCERPTS:\n\n{context_block}\n\n"
        f"QUESTION: {question}\n\n"
        'Respond with JSON: {"answer": "...", "citations": ["chunk_id", ...]}'
    )
    messages.append({"role": "user", "content": user_content})
    return messages
