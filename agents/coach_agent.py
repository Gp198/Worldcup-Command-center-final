from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any

import pandas as pd

from llm.mistral_analyst import MistralAnalyst
from simulator.monte_carlo import TournamentSimulator


class CoachAgent:
    """Ask-the-Coach agent for strategic tournament questions.

    Production-minded behaviour for demos:
    - fast simulation defaults and caps
    - in-memory simulation cache
    - Mistral timeout protection
    - local fallback that always returns an answer
    - diagnostics exposed to the UI
    """

    PLAYER_TEAM_MAP = {
        "mbapp": "France",
        "kylian": "France",
        "ronaldo": "Portugal",
        "cristiano": "Portugal",
        "messi": "Argentina",
        "vinicius": "Brazil",
        "vini": "Brazil",
        "neymar": "Brazil",
        "bellingham": "England",
        "kane": "England",
        "haaland": "Norway",
        "musiala": "Germany",
        "yamal": "Spain",
    }

    def __init__(self, teams_df: pd.DataFrame, matches_df: pd.DataFrame, mistral: MistralAnalyst | None = None):
        self.teams_df = teams_df.copy()
        self.matches_df = matches_df.copy()
        self.simulator = TournamentSimulator(self.teams_df)
        self.mistral = mistral or MistralAnalyst()
        self._projection_cache: dict[tuple[int, int], pd.DataFrame] = {}
        self._path_cache: dict[tuple[str, int, int], dict[str, Any]] = {}
        self._what_if_cache: dict[tuple[str, int, int, int], pd.DataFrame] = {}

    def answer(self, question: str, focus_team: str = "Portugal", n: int = 12000) -> dict[str, Any]:
        q = (question or "").lower()
        requested_n = int(n or 3000)
        # Keep demo responsive. The full 100k tournament simulation remains in
        # Tournament Intelligence; Ask the Coach is for fast strategy Q&A.
        effective_n = max(500, min(requested_n, 5000))
        diagnostics: list[str] = []
        if requested_n != effective_n:
            diagnostics.append(
                f"Simulation depth capped from {requested_n:,} to {effective_n:,} for responsive Ask-the-Coach analysis."
            )

        projection = self._cached_projection(effective_n, diagnostics)

        if "path" in q or "final" in q or "caminho" in q:
            insight = self._cached_path(focus_team, effective_n, diagnostics)
            local = self._path_response(focus_team, insight, projection)
            context = {
                "question_type": "path_to_final",
                "focus_team": focus_team,
                "simulations_used": effective_n,
                "path_insight": insight,
                "top_projection": projection.head(12).to_dict("records"),
            }
        elif "dark horse" in q or "underdog" in q or "surprise" in q or "surpresa" in q:
            dark = self.simulator.dark_horse_table(projection).head(8)
            local = self._dark_horse_response(dark)
            context = {
                "question_type": "dark_horse",
                "simulations_used": effective_n,
                "dark_horses": dark.to_dict("records"),
                "top_projection": projection.head(12).to_dict("records"),
            }
        elif "what happens" in q or "what if" in q or "misses" in q or "injur" in q or "lesion" in q or "doesn" in q or "play" in q:
            impacted_team = self._infer_impacted_team(q, focus_team)
            scenario_n = max(500, min(2000, effective_n // 2))
            scenario = self._cached_what_if(impacted_team, 10, scenario_n, diagnostics)
            local = self._what_if_response(impacted_team, scenario)
            context = {
                "question_type": "what_if",
                "focus_team": focus_team,
                "impacted_team": impacted_team,
                "simulations_used": scenario_n,
                "scenario": scenario.head(12).to_dict("records"),
            }
        else:
            dark = self.simulator.dark_horse_table(projection).head(5)
            path_n = max(500, min(2500, effective_n // 2))
            path = self._cached_path(focus_team, path_n, diagnostics)
            local = self._general_response(focus_team, projection, dark, path)
            context = {
                "question_type": "general_coach",
                "focus_team": focus_team,
                "simulations_used": effective_n,
                "top_projection": projection.head(12).to_dict("records"),
                "path": path,
                "dark_horses": dark.to_dict("records"),
            }

        ai_answer, ai_meta = self._ask_mistral(question, context, local)
        diagnostics.extend(ai_meta.get("diagnostics", []))
        return {
            "answer": ai_answer,
            "local_answer": local,
            "context": context,
            "projection": projection,
            "diagnostics": diagnostics,
            "ai_status": ai_meta.get("status", "unknown"),
            "simulations_requested": requested_n,
            "simulations_used": context.get("simulations_used", effective_n),
        }

    def _cached_projection(self, n: int, diagnostics: list[str]) -> pd.DataFrame:
        key = (n, len(self.matches_df))
        if key in self._projection_cache:
            diagnostics.append(f"Using cached champion projection for {n:,} simulations.")
            return self._projection_cache[key]
        diagnostics.append(f"Running champion projection with {n:,} simulations.")
        df = self.simulator.champion_projection_full(self.matches_df, n=n)
        self._projection_cache[key] = df
        return df

    def _cached_path(self, team: str, n: int, diagnostics: list[str]) -> dict[str, Any]:
        key = (team, n, len(self.matches_df))
        if key in self._path_cache:
            diagnostics.append(f"Using cached path simulation for {team} with {n:,} simulations.")
            return self._path_cache[key]
        diagnostics.append(f"Running path simulation for {team} with {n:,} simulations.")
        data = self.simulator.most_likely_path_to_final(team, self.matches_df, n=n)
        self._path_cache[key] = data
        return data

    def _cached_what_if(self, team: str, impact: int, n: int, diagnostics: list[str]) -> pd.DataFrame:
        key = (team, impact, n, len(self.matches_df))
        if key in self._what_if_cache:
            diagnostics.append(f"Using cached what-if simulation for {team} with {n:,} simulations.")
            return self._what_if_cache[key]
        diagnostics.append(f"Running what-if simulation for {team} with {n:,} simulations.")
        df = self.simulator.what_if_team_impact(team, impact=impact, matches_df=self.matches_df, n=n)
        self._what_if_cache[key] = df
        return df

    def _ask_mistral(self, question: str, context: dict[str, Any], local_answer: str) -> tuple[str, dict[str, Any]]:
        if not self.mistral.is_configured:
            return local_answer, {"status": "fallback_no_key", "diagnostics": ["Mistral API key not configured. Returned local coach fallback."]}

        prompt = (
            "You are the Ask the Coach module of World Cup Command Center 2026. "
            "Use the simulation context to answer like a senior national-team performance strategist. "
            "Be concise, strategic and practical. Do not invent live injuries or confirmed lineups. "
            "Use clean Markdown, avoid wide tables, and return the answer in under 500 words."
        )
        user_prompt = (
            f"User question: {question}\n\n"
            f"Simulation context: {context}\n\n"
            f"Local deterministic answer: {local_answer}\n\n"
            "Create a polished coach-style answer."
        )

        timeout_seconds = 18
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.mistral.client.complete, prompt, user_prompt)
                answer = future.result(timeout=timeout_seconds)
        except FuturesTimeoutError:
            return local_answer, {
                "status": "fallback_timeout",
                "diagnostics": [f"Mistral exceeded the {timeout_seconds}s Ask-the-Coach timeout. Returned local fallback."],
            }
        except Exception as exc:
            return local_answer, {
                "status": "fallback_exception",
                "diagnostics": [f"Mistral call failed: {exc}. Returned local fallback."],
            }

        if not answer or answer.strip().startswith("### Mistral Analyst") or "Mistral API returned an error" in answer:
            return local_answer, {
                "status": "fallback_mistral_error",
                "diagnostics": ["Mistral returned an error/empty response. Returned local fallback.", answer[:700]],
            }
        return answer, {"status": "mistral_success", "diagnostics": ["Mistral response completed successfully."]}

    def _path_response(self, team: str, insight: dict[str, Any], projection: pd.DataFrame) -> str:
        path = insight.get("most_likely_path", [])
        path_text = "\n".join(f"- {step}" for step in path) if path else "- The team did not reach the final often enough in this simulation sample to identify a stable path."
        return f"""
### Ask the Coach: {team}'s likely path to the final

**Round of 32 probability:** {insight['round_of_32_probability']}%  
**Final probability:** {insight['final_probability']}%  
**Champion probability:** {insight['champion_probability']}%

**Most common simulated path:**
{path_text}

**Coach interpretation:** the path is not a fixed prediction. It is the most frequent route observed across the simulation sample. Use it to prepare matchup-specific plans and stress-test tactical risks.
""".strip()

    def _dark_horse_response(self, dark: pd.DataFrame) -> str:
        if dark.empty:
            return "### Ask the Coach: Dark horses\n\nNo clear dark horse emerged from the current simulation sample."
        bullets = []
        for _, row in dark.head(5).iterrows():
            bullets.append(f"- **{row['team']}** — dark-horse score {row['dark_horse_score']}, champion probability {row['champion_probability']}%, final probability {row['final_probability']}%.")
        return "### Ask the Coach: Biggest dark horses\n\n" + "\n".join(bullets) + "\n\nThese teams combine lower pre-tournament expectation with enough model signal to create upset paths."

    def _what_if_response(self, impacted_team: str, scenario: pd.DataFrame) -> str:
        row = scenario.loc[scenario["team"] == impacted_team]
        if row.empty:
            return f"### Ask the Coach: What-if scenario\n\nNo scenario row available for {impacted_team}."
        r = row.iloc[0]
        return f"""
### Ask the Coach: What if {impacted_team} loses a key player?

**Base champion probability:** {r['champion_probability_base']}%  
**Scenario champion probability:** {r['champion_probability_scenario']}%  
**Delta:** {r['champion_delta']} percentage points

**Base final probability:** {r['final_probability_base']}%  
**Scenario final probability:** {r['final_probability_scenario']}%  
**Delta:** {r['final_delta']} percentage points

**Coach interpretation:** the model reduces attacking strength, squad depth and form. This does not confirm an injury; it shows how sensitive the tournament path is to the loss of a high-impact player.
""".strip()

    def _general_response(self, team: str, projection: pd.DataFrame, dark: pd.DataFrame, path: dict[str, Any]) -> str:
        top = projection.head(5)
        contenders = "\n".join(f"- **{r.team}** — {r.champion_probability}%" for r in top.itertuples())
        darks = "\n".join(f"- **{r.team}** — score {r.dark_horse_score}" for r in dark.itertuples())
        return f"""
### Ask the Coach: Strategic tournament view

**Top title contenders:**
{contenders}

**Dark-horse watchlist:**
{darks}

**{team} path signal:** final probability {path['final_probability']}%, champion probability {path['champion_probability']}%.

Use this module to test tournament strategy, matchup risk, key-player absence and likely knockout paths.
""".strip()

    def _infer_impacted_team(self, question: str, default_team: str) -> str:
        for token, team in self.PLAYER_TEAM_MAP.items():
            if token in question:
                return team
        for team in self.teams_df["team"].tolist():
            if team.lower() in question:
                return team
        return default_team
