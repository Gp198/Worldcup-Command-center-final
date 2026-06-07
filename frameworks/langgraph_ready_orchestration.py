"""LangGraph-ready orchestration contract.

This project intentionally runs without paid/extra orchestration dependencies by
using a lightweight deterministic graph in agents/orchestrator.py. This file
shows the node/edge contract you can map directly to LangGraph, CrewAI or
AutoGen when you want framework-managed execution.

Graph:
  Stats Agent -> Debate Agent
  Scout Agent -> Debate Agent
  Tactical Agent -> Debate Agent
  Player Agent -> Debate Agent
  News Agent -> Debate Agent
  Debate Agent -> Chief Analyst (Mistral)
"""

GRAPH_NODES = [
    "stats_agent",
    "scout_agent",
    "tactical_agent",
    "player_agent",
    "news_agent",
    "debate_agent",
    "chief_analyst_mistral",
]

GRAPH_EDGES = [
    ("stats_agent", "debate_agent"),
    ("scout_agent", "debate_agent"),
    ("tactical_agent", "debate_agent"),
    ("player_agent", "debate_agent"),
    ("news_agent", "debate_agent"),
    ("debate_agent", "chief_analyst_mistral"),
]


def describe_graph() -> dict:
    return {"nodes": GRAPH_NODES, "edges": GRAPH_EDGES, "mode": "local-lightweight-langgraph-ready"}
