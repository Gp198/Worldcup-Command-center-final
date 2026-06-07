# Phase 2 — Real Data Layer

This phase replaces the original mock-only dataset with a cache-first data architecture.

## Included data sources

- `data/elo_ratings.csv` — Elo rating cache
- `data/fifa_rankings.csv` — FIFA ranking cache
- `data/historical_results.csv` — recent international results used to compute form
- `data/players.csv` — squad/player dataset used to compute squad strength
- `data/sofascore_cache.json` — optional SofaScore cache placeholder

## Connectors

```text
connectors/
├── elo_connector.py
├── fifa_ranking_connector.py
├── historical_results_connector.py
├── players_connector.py
├── sofascore_connector.py
└── data_layer.py
```

## Build the enriched dataset

```bash
python scripts/build_data_layer.py
```

This creates:

```text
data/teams_phase2.csv
```

The Streamlit app calls `load_phase2_data()` directly, so it always builds the enriched dataset at runtime.

## SofaScore strategy

The SofaScore connector is intentionally optional and cache-first. The application does not rely on live SofaScore calls. This makes the MVP stable for demos and protects the project from endpoint changes, rate limits or access constraints.

Use SofaScore only where usage is permitted and prefer enriching `sofascore_cache.json` manually or through controlled, low-volume experiments.

## Data contract consumed by the model

The predictor expects these core columns:

- `team`
- `confederation`
- `fifa_rank`
- `elo`
- `recent_form`
- `attack_strength`
- `defense_strength`
- `squad_strength`

Phase 2 adds:

- `elo_rank`
- `fifa_points`
- `form_string`
- `goals_for_last_n`
- `goals_against_last_n`
- `top_player_rating`
- `squad_market_value_m`
- `players_tracked`
- `data_quality_score`
- `phase2_data_sources`
