from __future__ import annotations

import pandas as pd
from connectors.base import CSVConnector


class HistoricalResultsConnector(CSVConnector):
    name = "Historical Results"
    filename = "historical_results.csv"

    def form_table(self, last_n: int = 5) -> pd.DataFrame:
        df = self.load().copy()
        df["date"] = pd.to_datetime(df["date"])
        teams = sorted(set(df["home_team"]).union(set(df["away_team"])))
        rows = []
        for team in teams:
            matches = df[(df["home_team"] == team) | (df["away_team"] == team)].sort_values("date", ascending=False).head(last_n)
            points = 0
            gf = 0
            ga = 0
            labels = []
            for _, m in matches.sort_values("date").iterrows():
                is_home = m["home_team"] == team
                team_goals = int(m["home_goals"] if is_home else m["away_goals"])
                opp_goals = int(m["away_goals"] if is_home else m["home_goals"])
                gf += team_goals
                ga += opp_goals
                if team_goals > opp_goals:
                    points += 3
                    labels.append("W")
                elif team_goals == opp_goals:
                    points += 1
                    labels.append("D")
                else:
                    labels.append("L")
            max_points = max(1, len(matches) * 3)
            rows.append({
                "team": team,
                "recent_form": round(points / max_points, 3),
                "form_string": "-".join(labels),
                "goals_for_last_n": gf,
                "goals_against_last_n": ga,
                "matches_counted": len(matches),
            })
        return pd.DataFrame(rows)
