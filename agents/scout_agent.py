from __future__ import annotations

from rag.knowledge_retriever import SimpleKnowledgeRetriever


class ScoutAgent:
    def __init__(self, retriever: SimpleKnowledgeRetriever):
        self.retriever = retriever

    def analyze(self, home_team: str, away_team: str) -> dict:
        context = self.retriever.search(f"{home_team} {away_team} squad depth players strengths", top_k=3)
        return {
            "agent": "Scout Agent",
            "summary": "Scout view generated from team knowledge base and player/squad context.",
            "context": context,
        }
