from connectors.data_layer import load_phase2_data
from agents.orchestrator import AgentOrchestrator


def test_orchestrator_returns_graph_trace_without_api_key(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    teams_df, matches_df = load_phase2_data()
    orchestrator = AgentOrchestrator(teams_df, matches_df)
    result = orchestrator.run_intelligence_center("Portugal", "Brazil", "Create a short executive briefing.")
    assert "agent_reports" in result
    assert "graph_trace" in result
    assert len(result["graph_trace"]) >= 6
    assert "ai_answer" in result
