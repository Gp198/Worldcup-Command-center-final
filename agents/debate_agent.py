from __future__ import annotations

from typing import Any


class DebateAgent:
    """Challenge agent that stress-tests the first-pass analysis.

    This is deliberately deterministic. It identifies weak assumptions before the
    Chief Analyst calls the LLM, making the final briefing more credible.
    """

    def analyze(
        self,
        home_team: str,
        away_team: str,
        stats: dict[str, Any],
        scout: dict[str, Any],
        tactical: dict[str, Any],
        player: dict[str, Any],
        news: dict[str, Any],
    ) -> dict[str, Any]:
        prediction = stats.get("prediction")
        if prediction is None:
            return {
                "agent": "Debate Agent",
                "status": "completed",
                "summary": "No prediction object available to challenge.",
                "challenges": [],
                "counterarguments": [],
                "confidence": "low",
            }

        favorite = prediction.home_team if prediction.home_win >= prediction.away_win else prediction.away_team
        underdog = prediction.away_team if favorite == prediction.home_team else prediction.home_team
        spread = abs(float(prediction.home_win) - float(prediction.away_win))
        draw = float(prediction.draw)

        challenges = []
        counterarguments = []

        if spread < 12:
            challenges.append(
                "The win-probability spread is narrow, so the favourite should not be presented as a strong lock."
            )
        else:
            counterarguments.append(
                f"The model gives {favorite} a meaningful probability edge over {underdog}."
            )

        if draw >= 24:
            challenges.append(
                "Draw probability is material; game state, first goal timing and risk appetite may dominate the outcome."
            )

        player_risks = player.get("risks", []) if isinstance(player, dict) else []
        if player_risks:
            challenges.append("Player-level conclusions are limited by cached, non-live squad data.")

        if isinstance(news, dict) and news.get("context"):
            counterarguments.append("Knowledge/news context is available, but should be treated as supporting evidence, not live confirmation.")
        else:
            challenges.append("No reliable live news feed is active; avoid claiming confirmed injuries or tactical lineups.")

        tactical_summary = tactical.get("summary", "") if isinstance(tactical, dict) else ""
        if tactical_summary:
            counterarguments.append("Tactical-agent findings provide a qualitative explanation layer beyond raw probabilities.")

        summary = (
            f"The debate layer accepts {favorite} as the current model favourite, "
            f"but highlights {underdog}'s upset path and the need to separate statistical signal from match-day uncertainty."
        )

        return {
            "agent": "Debate Agent",
            "status": "completed",
            "summary": summary,
            "favorite": favorite,
            "underdog": underdog,
            "challenges": challenges,
            "counterarguments": counterarguments,
            "confidence": "medium-high" if spread >= 12 and draw < 24 else "medium",
        }
