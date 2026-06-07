from __future__ import annotations

import os
import platform
import time
from pathlib import Path
from typing import Any


def app_health() -> dict[str, Any]:
    required_files = ["app.py", "requirements.txt", "data/teams.csv", "data/matches.csv"]
    return {
        "status": "ok" if all(Path(p).exists() for p in required_files) else "degraded",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "mistral_configured": bool(os.getenv("MISTRAL_API_KEY")),
        "api_football_configured": bool(os.getenv("API_FOOTBALL_KEY")),
        "football_data_configured": bool(os.getenv("FOOTBALL_DATA_API_KEY")),
        "required_files": {p: Path(p).exists() for p in required_files},
    }
