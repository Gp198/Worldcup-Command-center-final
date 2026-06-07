from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from models.predictor import MatchPredictor


class TournamentSimulator:
    """Tournament simulation engine for the 48-team World Cup 2026 format.

    The real 2026 tournament has 12 groups of 4 teams. The top two teams in each
    group plus the eight best third-placed teams advance to a Round of 32.

    This simulator uses the local predictor as the probability engine and a
    practical deterministic bracket seeding approximation for a portfolio MVP.
    It is designed to be fast enough for 100,000 simulations on a laptop while
    staying transparent and explainable.
    """

    def __init__(self, teams_df: pd.DataFrame):
        self.teams_df = teams_df.copy()
        self.predictor = MatchPredictor(self.teams_df)
        self._prediction_cache: dict[tuple[str, str], object] = {}
        self._team_lookup = {row["team"]: row for _, row in self.teams_df.iterrows()}

    def _pred(self, home: str, away: str):
        key = (home, away)
        if key not in self._prediction_cache:
            self._prediction_cache[key] = self.predictor.predict(home, away)
        return self._prediction_cache[key]

    @staticmethod
    def _sample_outcome(prediction):
        roll = random.uniform(0, 100)
        if roll <= prediction.home_win:
            return prediction.home_team
        if roll <= prediction.home_win + prediction.draw:
            return "Draw"
        return prediction.away_team

    @staticmethod
    def _poisson_goals(xg: float) -> int:
        return int(np.random.poisson(max(0.05, float(xg))))

    def _team_strength(self, team: str) -> float:
        row = self._team_lookup.get(team)
        if row is None:
            return 0.0
        return (
            float(row.get("elo", 1800)) * 0.55
            + float(row.get("squad_strength", 78)) * 8
            + float(row.get("recent_form", 0.55)) * 500
            - float(row.get("fifa_rank", 99)) * 1.2
        )

    def simulate_matches(self, matches_df: pd.DataFrame, n: int = 1000) -> pd.DataFrame:
        counters: Dict[str, Counter] = {}
        for _, row in matches_df.iterrows():
            key = f"{row['home_team']} vs {row['away_team']}"
            counters[key] = Counter()
            pred = self._pred(row["home_team"], row["away_team"])
            for _ in range(n):
                counters[key][self._sample_outcome(pred)] += 1

        rows: List[dict] = []
        for match, counter in counters.items():
            total = sum(counter.values())
            for outcome, count in counter.items():
                rows.append({"match": match, "outcome": outcome, "probability": round(count / total * 100, 2)})
        return pd.DataFrame(rows)

    def champion_projection(self, n: int = 5000) -> pd.DataFrame:
        """Backward-compatible fast champion projection."""
        return self.champion_projection_full(matches_df=None, n=n)[["team", "champion_probability"]]

    def champion_projection_full(
        self,
        matches_df: Optional[pd.DataFrame] = None,
        n: int = 100000,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> pd.DataFrame:
        """Run a complete group + knockout simulation.

        Returns champion, final, semifinal, quarterfinal and knockout probabilities.
        """
        matches = matches_df if matches_df is not None else self._default_matches()
        champion_counter: Counter[str] = Counter()
        final_counter: Counter[str] = Counter()
        semi_counter: Counter[str] = Counter()
        quarter_counter: Counter[str] = Counter()
        r32_counter: Counter[str] = Counter()

        checkpoints = max(1, n // 100)
        for i in range(n):
            result = self._simulate_single_tournament(matches)
            champion_counter[result["champion"]] += 1
            for team in result["round_of_32"]:
                r32_counter[team] += 1
            for team in result["quarterfinalists"]:
                quarter_counter[team] += 1
            for team in result["semifinalists"]:
                semi_counter[team] += 1
            for team in result["finalists"]:
                final_counter[team] += 1
            if progress_callback and (i + 1) % checkpoints == 0:
                progress_callback((i + 1) / n)

        teams = sorted(self.teams_df["team"].unique().tolist())
        rows = []
        for team in teams:
            rows.append(
                {
                    "team": team,
                    "champion_probability": round(champion_counter[team] / n * 100, 2),
                    "final_probability": round(final_counter[team] / n * 100, 2),
                    "semifinal_probability": round(semi_counter[team] / n * 100, 2),
                    "quarterfinal_probability": round(quarter_counter[team] / n * 100, 2),
                    "round_of_32_probability": round(r32_counter[team] / n * 100, 2),
                }
            )
        return pd.DataFrame(rows).sort_values("champion_probability", ascending=False).reset_index(drop=True)

    def most_likely_path_to_final(self, team: str, matches_df: Optional[pd.DataFrame] = None, n: int = 15000) -> dict:
        matches = matches_df if matches_df is not None else self._default_matches()
        path_counter: Counter[tuple[str, ...]] = Counter()
        reach_final = 0
        reach_r32 = 0
        champion = 0
        for _ in range(n):
            result = self._simulate_single_tournament(matches, track_team=team)
            if team in result["round_of_32"]:
                reach_r32 += 1
            if team in result["finalists"]:
                reach_final += 1
                path_counter[tuple(result.get("tracked_path", []))] += 1
            if result["champion"] == team:
                champion += 1
        likely_path, count = path_counter.most_common(1)[0] if path_counter else (tuple(), 0)
        return {
            "team": team,
            "simulations": n,
            "round_of_32_probability": round(reach_r32 / n * 100, 2),
            "final_probability": round(reach_final / n * 100, 2),
            "champion_probability": round(champion / n * 100, 2),
            "most_likely_path": list(likely_path),
            "path_frequency_among_all_sims": round(count / n * 100, 2),
            "path_frequency_when_reaching_final": round(count / max(1, reach_final) * 100, 2),
        }

    def dark_horse_table(self, projection_df: pd.DataFrame) -> pd.DataFrame:
        df = projection_df.merge(
            self.teams_df[["team", "fifa_rank", "elo", "recent_form", "squad_strength"]],
            on="team",
            how="left",
        )
        # Higher score = lower FIFA expectation, but meaningful title path.
        df["dark_horse_score"] = (
            df["champion_probability"] * 2.0
            + df["final_probability"] * 0.75
            + df["semifinal_probability"] * 0.25
            + df["recent_form"] * 5
            + (df["fifa_rank"].fillna(99).clip(lower=12) - 12) * 0.06
        ).round(2)
        candidates = df[(df["fifa_rank"] >= 12) & ((df["champion_probability"] > 0) | (df["final_probability"] >= 1.0))]
        if candidates.empty:
            candidates = df[df["fifa_rank"] >= 12]
        return candidates.sort_values("dark_horse_score", ascending=False).reset_index(drop=True)

    def what_if_team_impact(
        self,
        team: str,
        impact: int = 10,
        matches_df: Optional[pd.DataFrame] = None,
        n: int = 12000,
    ) -> pd.DataFrame:
        matches = matches_df if matches_df is not None else self._default_matches()
        base = self.champion_projection_full(matches, n=n)
        scenario_df = self.teams_df.copy()
        mask = scenario_df["team"] == team
        scenario_df.loc[mask, "attack_strength"] = (scenario_df.loc[mask, "attack_strength"] - impact).clip(lower=50)
        scenario_df.loc[mask, "defense_strength"] = (scenario_df.loc[mask, "defense_strength"] - impact * 0.6).clip(lower=50)
        scenario_df.loc[mask, "squad_strength"] = (scenario_df.loc[mask, "squad_strength"] - impact).clip(lower=50)
        scenario_df.loc[mask, "recent_form"] = (scenario_df.loc[mask, "recent_form"] - impact / 100).clip(lower=0.1)
        scenario = TournamentSimulator(scenario_df).champion_projection_full(matches, n=n)
        merged = base.merge(scenario, on="team", suffixes=("_base", "_scenario"))
        merged["champion_delta"] = (merged["champion_probability_scenario"] - merged["champion_probability_base"]).round(2)
        merged["final_delta"] = (merged["final_probability_scenario"] - merged["final_probability_base"]).round(2)
        return merged.sort_values("champion_probability_base", ascending=False).reset_index(drop=True)

    def _simulate_single_tournament(self, matches_df: pd.DataFrame, track_team: Optional[str] = None) -> dict:
        standings = self._simulate_group_stage(matches_df)
        qualifiers = self._select_qualifiers(standings)
        r32 = qualifiers[:32]
        tracked_path: list[str] = []

        # Bracket approximation: strongest seed vs weakest seed, then natural pair progression.
        current = r32
        quarterfinalists = []
        semifinalists = []
        finalists = []
        round_name = "Round of 32"
        while len(current) > 1:
            pairs = self._pair_bracket(current)
            winners = []
            losers = []
            for a, b in pairs:
                winner = self._simulate_knockout(a, b)
                loser = b if winner == a else a
                winners.append(winner)
                losers.append(loser)
                if track_team and winner == track_team:
                    tracked_path.append(f"{round_name}: defeated {loser}")
                elif track_team and loser == track_team:
                    tracked_path.append(f"{round_name}: eliminated by {winner}")
            current = winners
            if len(current) == 16:
                round_name = "Round of 16"
            elif len(current) == 8:
                quarterfinalists = current.copy()
                round_name = "Quarter-finals"
            elif len(current) == 4:
                semifinalists = current.copy()
                round_name = "Semi-finals"
            elif len(current) == 2:
                finalists = current.copy()
                round_name = "Final"

        champion = current[0]
        if track_team and champion == track_team:
            tracked_path.append("Final result: champion")
        return {
            "champion": champion,
            "round_of_32": r32,
            "quarterfinalists": quarterfinalists,
            "semifinalists": semifinalists,
            "finalists": finalists,
            "tracked_path": tracked_path,
        }

    def _simulate_group_stage(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        teams = self.teams_df[["team", "group"]].copy()
        rows = []
        table = {
            team: {"team": team, "group": group, "pts": 0, "gf": 0, "ga": 0, "gd": 0, "wins": 0, "strength": self._team_strength(team)}
            for team, group in teams[["team", "group"]].itertuples(index=False)
        }
        for _, match in matches_df.iterrows():
            home = match["home_team"]
            away = match["away_team"]
            if home not in table or away not in table:
                continue
            pred = self._pred(home, away)
            hg = self._poisson_goals(pred.home_expected_goals)
            ag = self._poisson_goals(pred.away_expected_goals)
            # Avoid too many simulated 0-0s by applying outcome probabilities when goals tie.
            if hg == ag:
                outcome = self._sample_outcome(pred)
                if outcome == home:
                    hg += 1
                elif outcome == away:
                    ag += 1
            table[home]["gf"] += hg
            table[home]["ga"] += ag
            table[away]["gf"] += ag
            table[away]["ga"] += hg
            if hg > ag:
                table[home]["pts"] += 3
                table[home]["wins"] += 1
            elif ag > hg:
                table[away]["pts"] += 3
                table[away]["wins"] += 1
            else:
                table[home]["pts"] += 1
                table[away]["pts"] += 1
        for row in table.values():
            row["gd"] = row["gf"] - row["ga"]
            rows.append(row)
        return pd.DataFrame(rows)

    def _select_qualifiers(self, standings: pd.DataFrame) -> list[str]:
        qualified = []
        third_rows = []
        for group, gdf in standings.groupby("group"):
            ranked = gdf.sort_values(["pts", "gd", "gf", "wins", "strength"], ascending=False)
            qualified.extend(ranked.head(2)["team"].tolist())
            if len(ranked) >= 3:
                third_rows.append(ranked.iloc[2])
        thirds = pd.DataFrame(third_rows)
        if not thirds.empty:
            best_thirds = thirds.sort_values(["pts", "gd", "gf", "wins", "strength"], ascending=False).head(8)
            qualified.extend(best_thirds["team"].tolist())
        # Seed qualifiers for a stable bracket approximation.
        return sorted(qualified, key=lambda t: self._team_strength(t), reverse=True)

    @staticmethod
    def _pair_bracket(teams: list[str]) -> list[tuple[str, str]]:
        return [(teams[i], teams[-(i + 1)]) for i in range(len(teams) // 2)]

    def _simulate_knockout(self, team_a: str, team_b: str) -> str:
        pred = self._pred(team_a, team_b)
        # Redistribute draw probability to both teams based on win strengths.
        total_win = max(1e-6, pred.home_win + pred.away_win)
        a_prob = pred.home_win / total_win * 100
        return team_a if random.uniform(0, 100) <= a_prob else team_b

    def _default_matches(self) -> pd.DataFrame:
        # Full round-robin from groups if matches.csv is unavailable.
        rows = []
        for group, gdf in self.teams_df.groupby("group"):
            group_teams = gdf["team"].tolist()
            for i in range(len(group_teams)):
                for j in range(i + 1, len(group_teams)):
                    rows.append({"home_team": group_teams[i], "away_team": group_teams[j], "stage": f"Group {group}"})
        return pd.DataFrame(rows)
