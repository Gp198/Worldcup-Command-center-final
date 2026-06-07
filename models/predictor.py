from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import pandas as pd


@dataclass
class MatchPrediction:
    home_team: str
    away_team: str
    home_win: float
    draw: float
    away_win: float
    home_expected_goals: float
    away_expected_goals: float
    explanation_factors: Dict[str, float]


class MatchPredictor:
    def __init__(self, teams_df: pd.DataFrame):
        self.teams = teams_df.set_index("team")

    def _team(self, name: str) -> pd.Series:
        if name not in self.teams.index:
            raise ValueError(f"Team '{name}' not found in teams dataset")
        return self.teams.loc[name]

    @staticmethod
    def _normalize_elo(elo: float) -> float:
        return (elo - 1500) / 600

    def _strength_score(self, team: pd.Series) -> float:
        elo_component = self._normalize_elo(float(team["elo"])) * 0.35
        form_component = float(team["recent_form"]) * 0.25
        attack_component = float(team["attack_strength"]) / 100 * 0.18
        defense_component = float(team["defense_strength"]) / 100 * 0.14
        squad_component = float(team["squad_strength"]) / 100 * 0.08
        return elo_component + form_component + attack_component + defense_component + squad_component

    @staticmethod
    def _poisson_pmf(k: int, lam: float) -> float:
        return math.exp(-lam) * lam**k / math.factorial(k)

    def predict(self, home_team: str, away_team: str) -> MatchPrediction:
        home = self._team(home_team)
        away = self._team(away_team)

        home_score = self._strength_score(home)
        away_score = self._strength_score(away)
        diff = home_score - away_score

        base_xg = 1.35
        home_xg = max(0.35, base_xg + diff * 1.8 + 0.12)
        away_xg = max(0.35, base_xg - diff * 1.8)

        home_win = draw = away_win = 0.0
        max_goals = 7
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                p = self._poisson_pmf(h, home_xg) * self._poisson_pmf(a, away_xg)
                if h > a:
                    home_win += p
                elif h == a:
                    draw += p
                else:
                    away_win += p

        total = home_win + draw + away_win
        home_win, draw, away_win = home_win / total, draw / total, away_win / total

        return MatchPrediction(
            home_team=home_team,
            away_team=away_team,
            home_win=round(home_win * 100, 2),
            draw=round(draw * 100, 2),
            away_win=round(away_win * 100, 2),
            home_expected_goals=round(home_xg, 2),
            away_expected_goals=round(away_xg, 2),
            explanation_factors={
                "home_strength_score": round(home_score, 4),
                "away_strength_score": round(away_score, 4),
                "strength_difference": round(diff, 4),
                "home_elo": float(home["elo"]),
                "away_elo": float(away["elo"]),
                "home_recent_form": float(home["recent_form"]),
                "away_recent_form": float(away["recent_form"]),
            },
        )
