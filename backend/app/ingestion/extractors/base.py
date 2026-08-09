from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PageContent:
    page_number: int
    text: str


@dataclass
class ExtractionResult:
    pages: list[PageContent]
    metadata: dict = field(default_factory=dict)


class BaseExtractor(ABC):
    """Extracts per-page text content from an uploaded document."""

    @abstractmethod
    def extract(self, content: bytes, filename: str) -> ExtractionResult:
        raise NotImplementedError
