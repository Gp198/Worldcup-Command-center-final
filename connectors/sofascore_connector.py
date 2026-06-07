from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from connectors.base import DATA_DIR, ConnectorResult


class SofaScoreConnector:
    """Optional, cache-first SofaScore connector.

    This module is intentionally conservative: it reads from local cache by default.
    Network calls are disabled unless explicitly requested by the developer.
    Use only where permitted by the source terms and with low request volume.
    """

    name = "SofaScore Optional Connector"

    def __init__(self, cache_path: Path | None = None, sleep_seconds: float = 1.0):
        self.cache_path = cache_path or (DATA_DIR / "sofascore_cache.json")
        self.sleep_seconds = sleep_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "WorldCupCommandCenter/0.2 portfolio demo; cache-first",
            "Accept": "application/json,text/plain,*/*",
        })

    def load_cache(self) -> dict[str, Any]:
        if not self.cache_path.exists():
            return {"events": [], "teams": [], "players": []}
        with open(self.cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_cache(self, payload: dict[str, Any]) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def validate(self) -> ConnectorResult:
        cache = self.load_cache()
        rows = sum(len(cache.get(k, [])) for k in ["events", "teams", "players"])
        return ConnectorResult(self.name, self.cache_path, rows, "cache-ready")

    def _get_json(self, url: str) -> dict[str, Any]:
        time.sleep(self.sleep_seconds)
        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        return response.json()

    def fetch_url_to_cache_key(self, url: str, key: str) -> dict[str, Any]:
        """Manual helper for experimentation; not used automatically by the app."""
        cache = self.load_cache()
        payload = self._get_json(url)
        cache[key] = payload.get(key, payload)
        cache.setdefault("metadata", {})[key] = {"url": url, "fetched_at": time.time()}
        self.save_cache(cache)
        return cache

    def events_df(self) -> pd.DataFrame:
        cache = self.load_cache()
        return pd.DataFrame(cache.get("events", []))
