from __future__ import annotations

from models.predictor import MatchPredictor


class StatsAgent:
    def __init__(self, predictor: MatchPredictor):
        self.predictor = predictor

    def analyze(self, home_team: str, away_team: str) -> dict:
        prediction = self.predictor.predict(home_team, away_team)
        return {
            "agent": "Stats Agent",
            "summary": (
                f"{home_team} has {prediction.home_win}% win probability, "
                f"draw is {prediction.draw}%, and {away_team} has {prediction.away_win}%. "
                f"Expected goals: {home_team} {prediction.home_expected_goals}, "
                f"{away_team} {prediction.away_expected_goals}."
            ),
            "prediction": prediction,
        }
