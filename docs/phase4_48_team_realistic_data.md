
# Phase 4 — 48-Team Data Layer

This phase expands the MVP to all 48 FIFA World Cup 2026 teams and adds a realistic cached data layer for demo and portfolio use.

## Included datasets

- `data/teams.csv`: 48 teams, confederation, group, baseline attack/defense profiles.
- `data/fifa_rankings.csv`: cached FIFA ranking-style points and ranks.
- `data/elo_ratings.csv`: cached World Football Elo-style ratings.
- `data/historical_results.csv`: recent-form cache used to compute `recent_form` and `form_string`.
- `data/players.csv`: squad-strength cache with 5 tracked players per team.
- `data/matches.csv`: 72 group-stage fixtures.
- `data/sofascore_cache.json`: optional cache-first SofaScore connector placeholder.

## Important note

The project uses realistic cached seed data to support a zero-cost, reliable demo. Before production use, refresh the datasets from official or licensed sources and record the refresh timestamp.

## Recommended source hierarchy

1. FIFA official teams and ranking pages.
2. World Football Elo Ratings.
3. Public historical results datasets.
4. Licensed player/squad datasets or manually curated cache.
5. SofaScore only as optional cache-first enrichment when usage is permitted.
