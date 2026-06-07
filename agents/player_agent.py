from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


class PlayerAgent:
    """Player intelligence agent.

    Reads the Phase 4 players cache and produces player/squad findings for the
    selected match. The cache is intentionally local-first so the project can be
    demonstrated without paid APIs.
    """

    def __init__(self, players_df: pd.DataFrame | None = None, players_path: str = "data/players.csv"):
        if players_df is not None:
            self.players_df = players_df.copy()
        else:
            path = Path(players_path)
            self.players_df = pd.read_csv(path) if path.exists() else pd.DataFrame()

    def analyze(self, home_team: str, away_team: str) -> dict[str, Any]:
        home_players = self._team_players(home_team)
        away_players = self._team_players(away_team)

        home_top = self._top_players(home_players)
        away_top = self._top_players(away_players)
        home_depth = self._depth_score(home_players)
        away_depth = self._depth_score(away_players)

        depth_leader = home_team if home_depth >= away_depth else away_team
        rating_gap = round(abs(home_depth - away_depth), 2)

        summary = (
            f"{depth_leader} has the stronger tracked squad signal by {rating_gap} points "
            f"based on cached player ratings, market-value proxy and available squad depth."
        )

        evidence = [
            f"{home_team}: {len(home_players)} tracked players, depth index {home_depth}.",
            f"{away_team}: {len(away_players)} tracked players, depth index {away_depth}.",
            f"Top {home_team} profiles: {self._format_player_list(home_top)}.",
            f"Top {away_team} profiles: {self._format_player_list(away_top)}.",
        ]

        risks = [
            "Player cache is a realistic local dataset, not a live squad/lineup feed.",
            "Final match-day value depends on injuries, suspensions, tactical selection and minutes availability.",
        ]

        return {
            "agent": "Player Agent",
            "status": "completed",
            "summary": summary,
            "evidence": evidence,
            "risks": risks,
            "confidence": "medium",
            "data": {
                home_team: {
                    "depth_index": home_depth,
                    "tracked_players": len(home_players),
                    "top_players": home_top,
                },
                away_team: {
                    "depth_index": away_depth,
                    "tracked_players": len(away_players),
                    "top_players": away_top,
                },
            },
        }

    def _team_players(self, team: str) -> pd.DataFrame:
        if self.players_df.empty or "team" not in self.players_df.columns:
            return pd.DataFrame()
        return self.players_df[self.players_df["team"] == team].copy()

    @staticmethod
    def _top_players(df: pd.DataFrame, n: int = 5) -> list[dict[str, Any]]:
        if df.empty:
            return []
        sortable = df.copy()
        if "overall_rating" in sortable.columns:
            sortable = sortable.sort_values("overall_rating", ascending=False)
        records = []
        for _, row in sortable.head(n).iterrows():
            records.append(
                {
                    "player": row.get("player", "Unknown"),
                    "position": row.get("position", "N/A"),
                    "rating": float(row.get("overall_rating", 0)),
                    "market_value_m": float(row.get("market_value_m", 0)),
                    "status": row.get("status", "unknown"),
                }
            )
        return records

    @staticmethod
    def _depth_score(df: pd.DataFrame) -> float:
        if df.empty or "overall_rating" not in df.columns:
            return 0.0
        top = df.sort_values("overall_rating", ascending=False).head(8)
        rating = float(top["overall_rating"].mean()) if not top.empty else 0.0
        market = 0.0
        if "market_value_m" in top.columns and not top.empty:
            market = min(100.0, float(top["market_value_m"].mean()) / 1.6)
        return round((rating * 0.75) + (market * 0.25), 2)

    @staticmethod
    def _format_player_list(players: list[dict[str, Any]]) -> str:
        if not players:
            return "no tracked players"
        return ", ".join(f"{p['player']} ({p['position']}, {p['rating']:.1f})" for p in players[:4])
