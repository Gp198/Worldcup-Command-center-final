from __future__ import annotations

from typing import Any


class ChiefAnalystAgent:
    """Local Chief Analyst fallback and executive briefing formatter."""

    def synthesize(self, *reports: dict[str, Any]) -> str:
        report_map = {r.get("agent", f"Agent {i}"): r for i, r in enumerate(reports, start=1) if isinstance(r, dict)}
        stats = report_map.get("Stats Agent", {})
        scout = report_map.get("Scout Agent", {})
        tactical = report_map.get("Tactical Agent", {})
        player = report_map.get("Player Agent", {})
        news = report_map.get("News Agent", {})
        debate = report_map.get("Debate Agent", {})

        prediction = stats.get("prediction")
        if prediction is None:
            return "### Chief Analyst Briefing\n\nNo prediction data was available for this match."

        favorite = prediction.home_team if prediction.home_win >= prediction.away_win else prediction.away_team
        underdog = prediction.away_team if favorite == prediction.home_team else prediction.home_team

        def bullets(items: list[str]) -> str:
            if not items:
                return "- No specific evidence available."
            return "\n".join(f"- {item}" for item in items[:5])

        return f"""
### World Cup Executive Briefing

**Match:** {prediction.home_team} vs {prediction.away_team}  
**Current model favourite:** **{favorite}**  
**Primary uncertainty:** {underdog}'s upset path, draw pressure and match-day volatility.

#### Probability Signal
- {prediction.home_team} win: **{prediction.home_win}%**
- Draw: **{prediction.draw}%**
- {prediction.away_team} win: **{prediction.away_win}%**
- Expected goals: **{prediction.home_team} {prediction.home_expected_goals} xG** vs **{prediction.away_team} {prediction.away_expected_goals} xG**

#### Agent Findings
**Stats Agent:** {stats.get('summary', 'No stats summary available.')}  
**Scout Agent:** {scout.get('summary', 'No scout summary available.')}  
**Tactical Agent:** {tactical.get('summary', 'No tactical summary available.')}  
**Player Agent:** {player.get('summary', 'No player summary available.')}  
**News Agent:** {news.get('summary', 'No news summary available.')}

#### Debate Layer Challenge
{debate.get('summary', 'No debate challenge available.')}

**Main challenges:**
{bullets(debate.get('challenges', []))}

#### Executive Recommendation
Use the model as a decision-support system, not as a deterministic prediction. The next best action is to test what-if scenarios around injuries, fatigue, tactical setup and first-goal game state.
""".strip()
