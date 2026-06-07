from __future__ import annotations

import pandas as pd
from connectors.base import CSVConnector


class PlayersConnector(CSVConnector):
    name = "Players"
    filename = "players.csv"

    def squad_strength_table(self) -> pd.DataFrame:
        df = self.load().copy()
        available = df[df["status"].isin(["available", "monitor"])]
        table = available.groupby("team").agg(
            squad_strength=("overall_rating", "mean"),
            top_player_rating=("overall_rating", "max"),
            squad_market_value_m=("market_value_m", "sum"),
            players_tracked=("player", "count"),
        ).reset_index()
        table["squad_strength"] = table["squad_strength"].round(1)
        return table
