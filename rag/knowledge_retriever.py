from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


class SimpleKnowledgeRetriever:
    """Zero-cost MVP retriever using keyword overlap.

    This can later be replaced by ChromaDB/FAISS embeddings without changing
    the agent interfaces.
    """

    def __init__(self, kb_path: str = "knowledge_base"):
        self.kb_path = Path(kb_path)
        self.documents = self._load_documents()

    def _load_documents(self) -> List[Tuple[str, str]]:
        docs = []
        for path in self.kb_path.glob("*.md"):
            docs.append((path.name, path.read_text(encoding="utf-8")))
        return docs

    @staticmethod
    def _score(query: str, text: str) -> int:
        q_terms = set(query.lower().replace("/", " ").split())
        t_terms = set(text.lower().replace("/", " ").split())
        return len(q_terms.intersection(t_terms))

    def search(self, query: str, top_k: int = 3) -> List[str]:
        scored = sorted(
            [(self._score(query, text), name, text) for name, text in self.documents],
            reverse=True,
        )
        return [f"Source: {name}\n{text}" for score, name, text in scored[:top_k] if score > 0]
