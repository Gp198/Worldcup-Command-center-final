# Phase 5 — World Cup Intelligence Center

This phase upgrades the app from a single AI analyst call into a Level 3 multi-agent intelligence layer.

## Agent flow

```text
Stats Agent
Scout Agent
Tactical Agent
Player Agent
News Agent
        ↓
Debate Agent
        ↓
Chief Analyst Agent
Mistral Medium Latest
        ↓
World Cup Executive Briefing
```

## What changed

- Added `PlayerAgent` using `data/players.csv`.
- Added `DebateAgent` to challenge the first-pass findings.
- Rebuilt the `AgentOrchestrator` to run all specialist agents before calling Mistral.
- Updated the Mistral prompt to behave as a Chief Analyst.
- Added structured context passed to Mistral:
  - prediction probabilities
  - expected goals
  - team profiles
  - stats/scout/tactical/player/news reports
  - debate challenges
  - data limitations
- Updated the Streamlit app with a World Cup Intelligence Center view.

## Environment variables

```cmd
set MISTRAL_API_KEY=your_key_here
set MISTRAL_MODEL=mistral-medium-latest
streamlit run app.py
```

Optional for local corporate SSL/VPN demos only:

```cmd
set MISTRAL_SSL_VERIFY=false
```

## Notes

The project remains zero-cloud-cost and local-first. The data layer is realistic/cache-first, not a guaranteed live production feed. For production, plug in compliant live data sources for injuries, lineups, fixtures and live event statistics.
