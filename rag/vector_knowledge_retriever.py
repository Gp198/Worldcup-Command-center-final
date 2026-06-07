from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class VectorKnowledgeRetriever:
    """Local zero-cost RAG retriever using TF-IDF vectors.

    This gives the project a real retrieval layer without paid infrastructure.
    It can later be swapped with ChromaDB, FAISS or Azure AI Search while keeping
    the same `search(query, top_k)` interface used by the agents.
    """

    def __init__(self, kb_path: str = "knowledge_base"):
        self.kb_path = Path(kb_path)
        self.documents: List[Tuple[str, str]] = self._load_documents()
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = None
        if self.documents:
            self.matrix = self.vectorizer.fit_transform([text for _, text in self.documents])

    def _load_documents(self) -> List[Tuple[str, str]]:
        docs: List[Tuple[str, str]] = []
        for path in sorted(self.kb_path.glob("*.md")):
            text = path.read_text(encoding="utf-8").strip()
            if text:
                docs.append((path.name, text))
        return docs

    def search(self, query: str, top_k: int = 3) -> List[str]:
        if not self.documents or self.matrix is None:
            return []

        query_vector = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self.matrix).flatten()
        ranked_indexes = scores.argsort()[::-1][:top_k]

        results: List[str] = []
        for idx in ranked_indexes:
            score = float(scores[idx])
            if score <= 0:
                continue
            name, text = self.documents[idx]
            results.append(f"Source: {name}\nRelevance: {score:.3f}\n{text}")
        return results
