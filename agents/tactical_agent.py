from __future__ import annotations

from rag.knowledge_retriever import SimpleKnowledgeRetriever


class TacticalAgent:
    def __init__(self, retriever: SimpleKnowledgeRetriever):
        self.retriever = retriever

    def analyze(self, home_team: str, away_team: str) -> dict:
        context = self.retriever.search(f"{home_team} {away_team} tactical transitions possession compact defensive", top_k=3)
        return {
            "agent": "Tactical Agent",
            "summary": "Tactical risk assessment based on playing profiles and matchup dynamics.",
            "context": context,
        }
