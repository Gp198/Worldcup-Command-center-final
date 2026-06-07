from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable
from typing_extensions import TypedDict


@dataclass
class GraphNodeResult:
    name: str
    status: str
    elapsed_ms: int
    output: Any = None
    error: str | None = None


@dataclass
class GraphExecutionResult:
    mode: str
    trace: list[GraphNodeResult] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "trace": [r.__dict__ for r in self.trace],
            "state_keys": sorted(self.state.keys()),
        }


class AgentState(TypedDict, total=False):
    home_team: str
    away_team: str
    question: str
    stats: dict[str, Any]
    scout: dict[str, Any]
    tactical: dict[str, Any]
    player: dict[str, Any]
    news: dict[str, Any]
    debate: dict[str, Any]
    reports: dict[str, Any]
    briefing: str
    llm_context: dict[str, Any]
    ai_answer: str
    stats_agent_meta: dict[str, Any]
    scout_agent_meta: dict[str, Any]
    tactical_agent_meta: dict[str, Any]
    player_agent_meta: dict[str, Any]
    news_agent_meta: dict[str, Any]
    debate_agent_meta: dict[str, Any]
    chief_analyst_mistral_meta: dict[str, Any]


class LocalAgentGraphExecutor:
    """Production-safe state graph fallback.

    It executes nodes sequentially with the same node contract as the LangGraph
    path. This keeps Streamlit Community Cloud reliable even when LangGraph is
    not installed, while still exposing explicit graph traces and node outputs.
    """

    def __init__(self) -> None:
        self.mode = "local_state_graph"

    def run(self, initial_state: dict[str, Any], nodes: list[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]]) -> GraphExecutionResult:
        state = dict(initial_state)
        trace: list[GraphNodeResult] = []
        for name, node in nodes:
            start = time.perf_counter()
            try:
                update = node(state) or {}
                elapsed = int((time.perf_counter() - start) * 1000)
                state.update(update)
                state[f"{name}_meta"] = {"name": name, "status": "completed", "elapsed_ms": elapsed}
                trace.append(GraphNodeResult(name=name, status="completed", elapsed_ms=elapsed, output=self._brief(update)))
            except Exception as exc:  # noqa: BLE001 - visible diagnostics are intentional
                elapsed = int((time.perf_counter() - start) * 1000)
                state[f"{name}_error"] = str(exc)
                state[f"{name}_meta"] = {"name": name, "status": "failed", "elapsed_ms": elapsed, "error": str(exc)}
                trace.append(GraphNodeResult(name=name, status="failed", elapsed_ms=elapsed, error=str(exc)))
        return GraphExecutionResult(mode=self.mode, trace=trace, state=state)

    @staticmethod
    def _brief(update: dict[str, Any]) -> dict[str, Any]:
        return {k: (list(v.keys()) if isinstance(v, dict) else type(v).__name__) for k, v in update.items()}


class LangGraphAgentExecutor:
    """True LangGraph adapter with parallel specialist fan-out and fan-in.

    Graph topology:

        START
          ├─ stats_agent ┐
          ├─ scout_agent ┤
          ├─ tactical_agent ┤
          ├─ player_agent ┤──> debate_agent -> chief_analyst_mistral -> END
          └─ news_agent  ┘

    If LangGraph is not installed or fails at runtime, execution falls back to
    the local graph with the same state contract. This gives a genuine
    framework-managed path without making the demo brittle.
    """

    SPECIALIST_NODES = ["stats_agent", "scout_agent", "tactical_agent", "player_agent", "news_agent"]
    DEBATE_NODE = "debate_agent"
    CHIEF_NODE = "chief_analyst_mistral"

    def __init__(self) -> None:
        self.local = LocalAgentGraphExecutor()
        try:
            from langgraph.graph import END, START, StateGraph  # type: ignore
            self.StateGraph = StateGraph
            self.START = START
            self.END = END
            self.available = True
            self.mode = "langgraph_parallel_state_graph"
        except Exception:
            self.available = False
            self.mode = "local_state_graph_fallback"

    def run(self, initial_state: dict[str, Any], nodes: list[tuple[str, Callable[[dict[str, Any]], dict[str, Any]]]]) -> GraphExecutionResult:
        if not self.available:
            result = self.local.run(initial_state, nodes)
            result.mode = self.mode
            return result

        node_map = dict(nodes)
        expected = self.SPECIALIST_NODES + [self.DEBATE_NODE, self.CHIEF_NODE]
        if not all(name in node_map for name in expected):
            result = self.local.run(initial_state, nodes)
            result.mode = "local_state_graph_fallback_unsupported_topology"
            return result

        try:
            graph = self.StateGraph(AgentState)

            for node_name in expected:
                graph.add_node(node_name, self._make_node(node_name, node_map[node_name]))

            # True parallel fan-out for independent specialist analysis.
            for specialist in self.SPECIALIST_NODES:
                graph.add_edge(self.START, specialist)
                graph.add_edge(specialist, self.DEBATE_NODE)

            graph.add_edge(self.DEBATE_NODE, self.CHIEF_NODE)
            graph.add_edge(self.CHIEF_NODE, self.END)

            compiled = graph.compile()
            final_state = dict(compiled.invoke(dict(initial_state)))
            trace = self._build_trace(final_state, expected)
            return GraphExecutionResult(mode=self.mode, trace=trace, state=final_state)
        except Exception as exc:  # noqa: BLE001
            result = self.local.run(initial_state, nodes)
            result.mode = f"local_state_graph_fallback_langgraph_error: {exc}"
            return result

    def _make_node(self, node_name: str, fn: Callable[[dict[str, Any]], dict[str, Any]]):
        def _node(state: AgentState) -> dict[str, Any]:
            start = time.perf_counter()
            try:
                update = fn(dict(state)) or {}
                elapsed = int((time.perf_counter() - start) * 1000)
                return {**update, f"{node_name}_meta": {"name": node_name, "status": "completed", "elapsed_ms": elapsed}}
            except Exception as exc:  # noqa: BLE001
                elapsed = int((time.perf_counter() - start) * 1000)
                return {f"{node_name}_error": str(exc), f"{node_name}_meta": {"name": node_name, "status": "failed", "elapsed_ms": elapsed, "error": str(exc)}}
        return _node

    @staticmethod
    def _build_trace(state: dict[str, Any], nodes: list[str]) -> list[GraphNodeResult]:
        trace: list[GraphNodeResult] = []
        for name in nodes:
            meta = state.get(f"{name}_meta") or {"name": name, "status": "not_returned", "elapsed_ms": 0}
            trace.append(GraphNodeResult(
                name=meta.get("name", name),
                status=meta.get("status", "unknown"),
                elapsed_ms=int(meta.get("elapsed_ms", 0)),
                error=meta.get("error"),
            ))
        return trace
