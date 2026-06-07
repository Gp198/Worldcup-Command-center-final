from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@dataclass
class ConnectorResult:
    name: str
    path: Path
    rows: int
    status: str


class CSVConnector:
    """Small cache-first connector used by the zero-cost MVP."""

    filename: str
    name: str

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR

    @property
    def path(self) -> Path:
        return self.data_dir / self.filename

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"Missing data file: {self.path}")
        return pd.read_csv(self.path)

    def validate(self) -> ConnectorResult:
        df = self.load()
        return ConnectorResult(self.name, self.path, len(df), "ready")
