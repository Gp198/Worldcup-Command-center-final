from __future__ import annotations

from pathlib import Path
import pandas as pd

from connectors.elo_connector import EloConnector
from connectors.fifa_ranking_connector import FifaRankingConnector
from connectors.historical_results_connector import HistoricalResultsConnector
from connectors.players_connector import PlayersConnector
from connectors.sofascore_connector import SofaScoreConnector

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def build_master_team_dataset(data_dir: Path | None = None) -> pd.DataFrame:
    """Build a richer team master from real/cache data sources.

    This is the Phase 2 data contract consumed by the UI, predictor and simulator.
    The output keeps the original columns expected by the MVP and adds provenance fields.
    """
    data_dir = data_dir or DATA_DIR
    base = pd.read_csv(data_dir / "teams.csv")
    elo = EloConnector(data_dir).load()[["team", "elo", "elo_rank", "updated_at"]].rename(columns={"updated_at": "elo_updated_at"})
    fifa = FifaRankingConnector(data_dir).load()[["team", "fifa_rank", "fifa_points", "updated_at"]].rename(columns={"updated_at": "fifa_updated_at"})
    form = HistoricalResultsConnector(data_dir).form_table(last_n=5)
    squad = PlayersConnector(data_dir).squad_strength_table()

    # Preserve columns that are not replaced by the richer sources.
    for col in ["elo", "fifa_rank", "recent_form", "squad_strength"]:
        if col in base.columns:
            base = base.drop(columns=[col])

    df = base.merge(elo, on="team", how="left")
    df = df.merge(fifa, on="team", how="left")
    df = df.merge(form, on="team", how="left")
    df = df.merge(squad, on="team", how="left")

    # Make sure the app always has stable values.
    df["elo"] = df["elo"].fillna(1800)
    df["elo_rank"] = df["elo_rank"].fillna(99)
    df["fifa_rank"] = df["fifa_rank"].fillna(99)
    df["fifa_points"] = df["fifa_points"].fillna(1500)
    df["recent_form"] = df["recent_form"].fillna(0.55)
    df["form_string"] = df["form_string"].fillna("W-D-W-L-W")
    df["squad_strength"] = df["squad_strength"].fillna(78)
    df["top_player_rating"] = df["top_player_rating"].fillna(df["squad_strength"])
    df["squad_market_value_m"] = df["squad_market_value_m"].fillna(0)
    df["players_tracked"] = df["players_tracked"].fillna(0).astype(int)

    # Derive attack/defense from existing baseline but enrich slightly with Elo and player strength.
    if "attack_strength" not in df.columns:
        df["attack_strength"] = 75
    if "defense_strength" not in df.columns:
        df["defense_strength"] = 75

    elo_boost = ((df["elo"] - 1800) / 20).clip(-8, 10)
    squad_boost = ((df["squad_strength"] - 80) / 2).clip(-5, 7)
    df["attack_strength"] = (df["attack_strength"] + elo_boost + squad_boost).clip(55, 98).round(1)
    df["defense_strength"] = (df["defense_strength"] + (elo_boost * 0.8) + (squad_boost * 0.6)).clip(55, 98).round(1)
    df["squad_strength"] = df["squad_strength"].clip(55, 98).round(1)

    df["data_quality_score"] = (
        0.35 * (df["players_tracked"].clip(0, 5) / 5)
        + 0.30 * (df["matches_counted"].clip(0, 5) / 5)
        + 0.20
        + 0.15
    ).round(2)
    df["phase2_data_sources"] = "Elo cache + FIFA ranking cache + historical results + players dataset"
    return df.sort_values(["fifa_rank", "team"]).reset_index(drop=True)


def load_phase2_data(data_dir: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    data_dir = data_dir or DATA_DIR
    teams = build_master_team_dataset(data_dir)
    matches = pd.read_csv(data_dir / "matches.csv")
    return teams, matches


def connector_status(data_dir: Path | None = None) -> pd.DataFrame:
    data_dir = data_dir or DATA_DIR
    connectors = [
        EloConnector(data_dir),
        FifaRankingConnector(data_dir),
        HistoricalResultsConnector(data_dir),
        PlayersConnector(data_dir),
        SofaScoreConnector(data_dir / "sofascore_cache.json"),
    ]
    rows = []
    for connector in connectors:
        result = connector.validate()
        rows.append({
            "connector": result.name,
            "rows": result.rows,
            "status": result.status,
            "path": str(result.path),
        })
    return pd.DataFrame(rows)
