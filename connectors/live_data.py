from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import requests
import urllib3
from requests.exceptions import SSLError


@dataclass
class ProviderSnapshot:
    provider: str
    status: str
    source_mode: str
    records: int
    message: str
    payload: dict[str, Any]
    fetched_at: float

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["fetched_at_iso"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.fetched_at))
        return data


class LiveFootballDataHub:
    """Cache-first live data hub.

    Designed for production readiness without fragile scraping. It supports:
    - API-Football when API_FOOTBALL_KEY is configured.
    - football-data.org when FOOTBALL_DATA_API_KEY is configured.
    - SofaScore cache enrichment without depending on unofficial live endpoints.
    - Local fallback so demos never fail.
    """

    def __init__(self, cache_path: str = "data/live_cache.json", timeout: int = 10) -> None:
        self.cache_path = Path(cache_path)
        self.timeout = int(os.getenv("LIVE_DATA_TIMEOUT_SECONDS", timeout))
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.ssl_verify = os.getenv("LIVE_DATA_SSL_VERIFY", "true").lower() not in {"0", "false", "no"}
        if not self.ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _get(self, url: str, headers: dict[str, str]) -> tuple[requests.Response | None, str | None, str]:
        """GET with corporate SSL resilience.

        Some corporate laptops/VPNs inject a self-signed certificate. The first
        call uses secure verification by default. If that specific SSL failure
        happens, the method retries once with verification disabled and clearly
        marks the response mode as ssl_retry_unverified. For production, install
        the corporate CA certificate instead of relying on this fallback.
        """
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout, verify=self.ssl_verify)
            return resp, None, "live_api" if self.ssl_verify else "live_api_unverified_ssl"
        except SSLError as exc:
            if self.ssl_verify:
                try:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    resp = requests.get(url, headers=headers, timeout=self.timeout, verify=False)
                    return resp, f"SSL verification failed; retried with verify=False for local demo. Original: {exc}", "live_api_ssl_retry_unverified"
                except Exception as retry_exc:  # noqa: BLE001
                    return None, str(retry_exc), "live_api_ssl_error"
            return None, str(exc), "live_api_ssl_error"
        except Exception as exc:  # noqa: BLE001
            return None, str(exc), "live_api_error"

    def health(self) -> list[dict[str, Any]]:
        return [
            self._provider_health("API-Football", "API_FOOTBALL_KEY"),
            self._provider_health("football-data.org", "FOOTBALL_DATA_API_KEY"),
            {"provider": "SofaScore cache", "configured": self._sofascore_cache_exists(), "mode": "cache_first", "production_note": "Use only where permitted by terms/licensing."},
            {"provider": "Local datasets", "configured": True, "mode": "fallback", "production_note": "Always available for demo resilience."},
        ]

    def get_match_context(self, home_team: str, away_team: str) -> dict[str, Any]:
        snapshots = [
            self._fetch_api_football(home_team, away_team),
            self._fetch_football_data(home_team, away_team),
            self._fetch_sofascore_cache(home_team, away_team),
        ]
        self._write_cache([s.to_dict() for s in snapshots])
        return {
            "home_team": home_team,
            "away_team": away_team,
            "providers": [s.to_dict() for s in snapshots],
            "live_data_ready": any(s.status == "ok" for s in snapshots),
            "data_contract": {
                "fixtures": "planned",
                "injuries": "planned",
                "lineups": "planned",
                "ratings": "planned/cache-first",
            },
        }


    def get_world_cup_snapshot(self) -> dict[str, Any]:
        """Fetch a lightweight World Cup snapshot from configured providers.

        football-data.org exposes the World Cup competition under the WC code for
        the account shown in the UI. The method is intentionally defensive: it
        returns a usable local/cache snapshot even when the API is not configured,
        rate-limited or unavailable.
        """
        snapshots = [
            self._fetch_football_data_world_cup(),
            self._fetch_api_football_status(),
            self._fetch_sofascore_cache("World Cup", "2026"),
        ]
        self._write_cache([s.to_dict() for s in snapshots])
        return {
            "providers": [s.to_dict() for s in snapshots],
            "live_data_ready": any(s.status == "ok" for s in snapshots),
            "snapshot_contract": {
                "fixtures": "football-data.org WC endpoint where available",
                "provider_status": "API-Football status endpoint",
                "cache_enrichment": "SofaScore cache-first local file",
            },
        }

    def _fetch_football_data_world_cup(self) -> ProviderSnapshot:
        key = os.getenv("FOOTBALL_DATA_API_KEY")
        if not key:
            return self._snapshot("football-data.org WC", "skipped", "not_configured", 0, "FOOTBALL_DATA_API_KEY not configured.", {})
        try:
            url = "https://api.football-data.org/v4/competitions/WC"
            resp, warning, mode = self._get(url, headers={"X-Auth-Token": key})
            if resp is None:
                return self._snapshot("football-data.org WC", "error", mode, 0, warning or "Request failed.", {})
            payload = resp.json() if resp.content else {}
            records = 1 if resp.ok else 0
            msg = f"HTTP {resp.status_code}" + (f" · {warning}" if warning else "")
            return self._snapshot("football-data.org WC", "ok" if resp.ok else "error", mode, records, msg, payload)
        except Exception as exc:  # noqa: BLE001
            return self._snapshot("football-data.org WC", "error", "live_api", 0, str(exc), {})

    def _fetch_api_football_status(self) -> ProviderSnapshot:
        return self._fetch_api_football("World Cup", "2026")

    def _provider_health(self, provider: str, env_name: str) -> dict[str, Any]:
        return {
            "provider": provider,
            "configured": bool(os.getenv(env_name)),
            "mode": "live_api" if os.getenv(env_name) else "not_configured",
            "env_var": env_name,
            "ssl_verify": self.ssl_verify,
        }

    def _fetch_api_football(self, home_team: str, away_team: str) -> ProviderSnapshot:
        key = os.getenv("API_FOOTBALL_KEY")
        if not key:
            return self._snapshot("API-Football", "skipped", "not_configured", 0, "API_FOOTBALL_KEY not configured.", {})
        try:
            # Lightweight status call. Real fixture endpoints can be added once a plan and league/season IDs are selected.
            url = "https://v3.football.api-sports.io/status"
            resp, warning, mode = self._get(url, headers={"x-apisports-key": key})
            if resp is None:
                return self._snapshot("API-Football", "error", mode, 0, warning or "Request failed.", {})
            payload = resp.json() if resp.content else {}
            msg = f"HTTP {resp.status_code}" + (f" · {warning}" if warning else "")
            return self._snapshot("API-Football", "ok" if resp.ok else "error", mode, 1 if resp.ok else 0, msg, payload)
        except Exception as exc:  # noqa: BLE001
            return self._snapshot("API-Football", "error", "live_api", 0, str(exc), {})

    def _fetch_football_data(self, home_team: str, away_team: str) -> ProviderSnapshot:
        key = os.getenv("FOOTBALL_DATA_API_KEY")
        if not key:
            return self._snapshot("football-data.org", "skipped", "not_configured", 0, "FOOTBALL_DATA_API_KEY not configured.", {})
        try:
            url = "https://api.football-data.org/v4/competitions"
            resp, warning, mode = self._get(url, headers={"X-Auth-Token": key})
            if resp is None:
                return self._snapshot("football-data.org", "error", mode, 0, warning or "Request failed.", {})
            payload = resp.json() if resp.content else {}
            count = len(payload.get("competitions", [])) if isinstance(payload, dict) else 0
            msg = f"HTTP {resp.status_code}" + (f" · {warning}" if warning else "")
            return self._snapshot("football-data.org", "ok" if resp.ok else "error", mode, count, msg, payload)
        except Exception as exc:  # noqa: BLE001
            return self._snapshot("football-data.org", "error", "live_api", 0, str(exc), {})

    def _fetch_sofascore_cache(self, home_team: str, away_team: str) -> ProviderSnapshot:
        path = Path("data/sofascore_cache.json")
        if not path.exists():
            return self._snapshot("SofaScore cache", "skipped", "cache_first", 0, "No local SofaScore cache found.", {})
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return self._snapshot("SofaScore cache", "ok", "cache_first", len(payload) if isinstance(payload, list) else 1, "Loaded local cache.", payload if isinstance(payload, dict) else {"items": payload[:5] if isinstance(payload, list) else payload})
        except Exception as exc:  # noqa: BLE001
            return self._snapshot("SofaScore cache", "error", "cache_first", 0, str(exc), {})

    def _snapshot(self, provider: str, status: str, mode: str, records: int, message: str, payload: dict[str, Any]) -> ProviderSnapshot:
        return ProviderSnapshot(provider=provider, status=status, source_mode=mode, records=records, message=message, payload=payload, fetched_at=time.time())

    def _write_cache(self, snapshots: list[dict[str, Any]]) -> None:
        self.cache_path.write_text(json.dumps({"snapshots": snapshots}, indent=2), encoding="utf-8")

    @staticmethod
    def _sofascore_cache_exists() -> bool:
        return Path("data/sofascore_cache.json").exists()
