# Live Data Strategy

The live data design is cache-first and provider-agnostic.

## Providers

- API-Football: optional API provider for fixtures, teams and football metadata.
- football-data.org: optional API provider for competitions and fixtures.
- SofaScore: optional cache enrichment only, because live usage must respect provider terms.
- Local datasets: always available fallback.

## Why cache-first?

A demo or production dashboard should not fail because a provider is unavailable, rate-limited or not configured.

The app therefore follows this strategy:

```text
Live API available → fetch and cache
Live API unavailable → use local cache
No cache → use deterministic local datasets
```

## Production recommendation

For a real product, use a licensed data provider and define a scheduled ingestion pipeline.
