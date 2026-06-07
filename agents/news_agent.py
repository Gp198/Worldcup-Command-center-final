from __future__ import annotations

from rag.knowledge_retriever import SimpleKnowledgeRetriever


class NewsAgent:
    def __init__(self, retriever: SimpleKnowledgeRetriever):
        self.retriever = retriever

    def analyze(self, home_team: str, away_team: str) -> dict:
        context = self.retriever.search(f"{home_team} {away_team} injuries suspensions news risk", top_k=2)
        return {
            "agent": "News Agent",
            "summary": "MVP offline news check. Replace with live compliant sources in production.",
            "context": context,
        }
