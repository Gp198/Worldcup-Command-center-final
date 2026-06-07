from __future__ import annotations

from connectors.base import CSVConnector


class FifaRankingConnector(CSVConnector):
    name = "FIFA Rankings"
    filename = "fifa_rankings.csv"
