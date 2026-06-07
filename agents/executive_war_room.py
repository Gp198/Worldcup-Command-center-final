from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from llm.mistral_analyst import MistralAnalyst
from simulator.monte_carlo import TournamentSimulator
from connectors.live_data import LiveFootballDataHub


class ExecutiveWarRoom:
    """One-click executive briefing generator.

    This is the 'wow' layer for demos: it combines live-provider diagnostics,
    cached football data, a fast tournament projection, risk detection and a
    Mistral-generated boardroom-style briefing. It is designed to never block a
    demo: if live APIs or Mistral are unavailable, it returns a deterministic
    local executive report.
    """

    def __init__(
        self,
        teams_df: pd.DataFrame,
        matches_df: pd.DataFrame,
        live_hub: LiveFootballDataHub,
        mistral: MistralAnalyst | None = None,
    ) -> None:
        self.teams_df = teams_df.copy()
        self.matches_df = matches_df.copy()
        self.live_hub = live_hub
        self.mistral = mistral or MistralAnalyst()
        self.simulator = TournamentSimulator(self.teams_df)
        self._cache: dict[tuple[str, int], dict[str, Any]] = {}

    def generate(self, focus_team: str = "Portugal", simulations: int = 10000) -> dict[str, Any]:
        n = max(1000, min(int(simulations or 10000), 25000))
        cache_key = (focus_team, n)
        if cache_key in self._cache:
            cached = dict(self._cache[cache_key])
            cached["cache_status"] = "cache_hit"
            return cached

        provider_health = self.live_hub.health()
        world_cup_snapshot = self.live_hub.get_world_cup_snapshot()
        projection = self.simulator.champion_projection_full(self.matches_df, n=n)
        dark_horses = self.simulator.dark_horse_table(projection).head(8)
        focus_row = projection.loc[projection["team"] == focus_team]
        focus_projection = focus_row.iloc[0].to_dict() if not focus_row.empty else {}
        top_contenders = projection.head(10).to_dict("records")

        risks = self._detect_risks(focus_team, projection, dark_horses, world_cup_snapshot)
        local = self._local_briefing(
            focus_team=focus_team,
            simulations=n,
            focus_projection=focus_projection,
            top_contenders=top_contenders,
            dark_horses=dark_horses.to_dict("records"),
            risks=risks,
            world_cup_snapshot=world_cup_snapshot,
        )
        ai_answer, ai_status = self._ask_mistral(
            focus_team=focus_team,
            simulations=n,
            focus_projection=focus_projection,
            top_contenders=top_contenders,
            dark_horses=dark_horses.to_dict("records"),
            risks=risks,
            world_cup_snapshot=world_cup_snapshot,
            local=local,
        )
        result = {
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "focus_team": focus_team,
            "simulations_used": n,
            "provider_health": provider_health,
            "world_cup_snapshot": world_cup_snapshot,
            "projection": projection,
            "top_contenders": top_contenders,
            "dark_horses": dark_horses,
            "focus_projection": focus_projection,
            "risk_register": risks,
            "local_briefing": local,
            "executive_briefing": ai_answer,
            "ai_status": ai_status,
            "cache_status": "generated",
        }
        self._cache[cache_key] = result
        return result

    def _ask_mistral(self, **kwargs: Any) -> tuple[str, str]:
        if not self.mistral.is_configured:
            return kwargs["local"], "fallback_no_mistral_key"
        context = {k: v for k, v in kwargs.items() if k != "local"}
        question = (
            "Create a polished executive war-room briefing for the World Cup Intelligence Center. "
            "Use the projection, risk register, live-data snapshot and dark-horse table. "
            "Structure it with: Executive Summary, Tournament Signals, Risk Register, Recommended Actions. "
            "Be concise, technical and suitable for LinkedIn/Medium demo. Do not invent confirmed live news."
        )
        try:
            answer = self.mistral.answer(question=question, context=context)
        except Exception as exc:  # noqa: BLE001
            return kwargs["local"] + f"\n\n_Mistral fallback reason: {exc}_", "fallback_mistral_exception"
        if not answer or "Mistral API returned an error" in answer:
            return kwargs["local"], "fallback_mistral_error"
        return answer, "mistral_success"

    @staticmethod
    def _detect_risks(
        focus_team: str,
        projection: pd.DataFrame,
        dark_horses: pd.DataFrame,
        world_cup_snapshot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        risks: list[dict[str, Any]] = []
        row = projection.loc[projection["team"] == focus_team]
        if not row.empty:
            r = row.iloc[0]
            if float(r.get("champion_probability", 0)) < 10:
                risks.append({"severity": "medium", "risk": f"{focus_team} is not among the strongest title signals.", "action": "Stress-test knockout matchups and identify tactical edges."})
            if float(r.get("round_of_16_probability", r.get("round_16_probability", 0))) < 65:
                risks.append({"severity": "high", "risk": f"{focus_team} qualification path shows volatility.", "action": "Prioritize group-stage point optimization and rotation plans."})
        if not dark_horses.empty:
            dh = dark_horses.iloc[0]
            risks.append({"severity": "watch", "risk": f"{dh['team']} appears as the strongest dark-horse signal.", "action": "Monitor upset paths and potential bracket disruption."})
        if not world_cup_snapshot.get("live_data_ready"):
            risks.append({"severity": "data", "risk": "No live data provider returned a fresh successful snapshot.", "action": "Use local cache now; refresh providers before public demos."})
        return risks

    @staticmethod
    def _local_briefing(
        focus_team: str,
        simulations: int,
        focus_projection: dict[str, Any],
        top_contenders: list[dict[str, Any]],
        dark_horses: list[dict[str, Any]],
        risks: list[dict[str, Any]],
        world_cup_snapshot: dict[str, Any],
    ) -> str:
        champion = focus_projection.get("champion_probability", 0)
        final = focus_projection.get("final_probability", 0)
        top = top_contenders[0]["team"] if top_contenders else "No team"
        dark = dark_horses[0]["team"] if dark_horses else "No dark horse"
        risk_lines = "\n".join(f"- **{r['severity'].upper()}** — {r['risk']} Action: {r['action']}" for r in risks) or "- No critical risks detected in this sample."
        return f"""
## Executive War Room Briefing

**Focus team:** {focus_team}  
**Simulation depth:** {simulations:,} tournament runs  
**Live data mode:** {'live/cache hybrid' if world_cup_snapshot.get('live_data_ready') else 'local cache fallback'}

### Executive Summary
{focus_team} currently projects at **{champion:.2f}%** to win the tournament and **{final:.2f}%** to reach the final. The strongest title signal in the current projection is **{top}**.

### Tournament Signals
- Biggest dark-horse signal: **{dark}**.
- Top contenders and qualification volatility should be monitored before every public briefing.
- The platform is operating with resilient fallbacks, so the demo remains available even if live providers are unavailable.

### Risk Register
{risk_lines}

### Recommended Actions
- Refresh live providers before sharing the public demo.
- Run a 100,000-simulation projection for the final published screenshot.
- Use Ask the Coach for stakeholder-friendly scenario explanations.
""".strip()
