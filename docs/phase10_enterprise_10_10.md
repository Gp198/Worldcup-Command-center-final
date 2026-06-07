# Phase 10 — Enterprise 10/10 Upgrade

This phase turns the portfolio MVP into a production-ready AI engineering showcase.

## What changed

### 1. Real Agent Orchestration

The project now includes a graph-based orchestration layer:

- `orchestration/agent_graph.py`
- Local state graph executor by default
- Optional LangGraph executor when `langgraph` is installed
- Execution trace returned to the UI
- Node-level timing and error diagnostics

Graph:

```text
Stats Agent
  ↓
Scout Agent
  ↓
Tactical Agent
  ↓
Player Agent
  ↓
News Agent
  ↓
Debate Agent
  ↓
Chief Analyst / Mistral
```

### 2. Live Data Hub

The project now includes a cache-first live data abstraction:

- API-Football support via `API_FOOTBALL_KEY`
- football-data.org support via `FOOTBALL_DATA_API_KEY`
- SofaScore cache-first strategy
- Local fallback datasets
- Provider health UI

This avoids hard dependencies on fragile scraping while keeping the solution production-friendly.

### 3. Enterprise Deployment

Added:

- Dockerfile
- docker-compose.yml
- GitHub Actions CI
- tests
- health diagnostics
- Streamlit secrets example
- Makefile
- production readiness page

## How to run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How to run with Docker

```bash
docker compose up --build
```

## Optional LangGraph execution

```bash
pip install -r requirements-agentic.txt
streamlit run app.py
```

The orchestrator will automatically use LangGraph if available and fallback to the local state graph otherwise.

## Environment variables

```bash
MISTRAL_API_KEY=
MISTRAL_MODEL=mistral-medium-latest
MISTRAL_TIMEOUT_SECONDS=12
API_FOOTBALL_KEY=
FOOTBALL_DATA_API_KEY=
LIVE_DATA_TIMEOUT_SECONDS=10
LOG_LEVEL=INFO
```
