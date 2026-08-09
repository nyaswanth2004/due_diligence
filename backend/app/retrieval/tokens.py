import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercased alphanumeric tokens shared by BM25 and hash embeddings."""
    return _TOKEN_RE.findall(text.lower())
