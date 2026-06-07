from __future__ import annotations

from connectors.base import CSVConnector


class EloConnector(CSVConnector):
    name = "Elo Ratings"
    filename = "elo_ratings.csv"
