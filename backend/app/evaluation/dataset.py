"""Golden evaluation dataset for retrieval and grounded-QA quality."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvaluationQuestion:
    question: str
    golden_chunk_ids: list[str] = field(default_factory=list)
    golden_answer_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "golden_chunk_ids": self.golden_chunk_ids,
            "golden_answer_terms": self.golden_answer_terms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationQuestion":
        return cls(
            question=data["question"],
            golden_chunk_ids=list(data.get("golden_chunk_ids") or []),
            golden_answer_terms=list(data.get("golden_answer_terms") or []),
        )


@dataclass
class EvaluationDataset:
    questions: list[EvaluationQuestion] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"questions": [q.to_dict() for q in self.questions]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationDataset":
        return cls(questions=[EvaluationQuestion.from_dict(q) for q in data.get("questions", [])])

    @classmethod
    def load(cls, path: str | Path) -> "EvaluationDataset":
        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def save(self, path: str | Path) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
