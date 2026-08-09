from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class VerificationReport:
    """Result of checking an LLM's citations against the provided context."""

    valid: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)


class CitationVerifier:
    """Grounding guardrail.

    An LLM can only cite chunks that were actually provided as context. Any
    other id (hallucinated or stale) is dropped and reported so downstream
    consumers can see exactly what was removed and why.
    """

    def verify(
        self,
        cited_ids: Iterable[str],
        allowed_ids: Iterable[str],
    ) -> VerificationReport:
        allowed = set(allowed_ids)
        report = VerificationReport()
        seen: set[str] = set()
        for chunk_id in cited_ids:
            if chunk_id in allowed and chunk_id not in seen:
                report.valid.append(chunk_id)
                seen.add(chunk_id)
            elif chunk_id not in allowed and chunk_id not in report.dropped:
                report.dropped.append(chunk_id)
        return report
