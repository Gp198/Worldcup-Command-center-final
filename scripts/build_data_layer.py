from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from connectors.data_layer import build_master_team_dataset, connector_status  # noqa: E402


def main() -> None:
    data_dir = ROOT / "data"
    teams = build_master_team_dataset(data_dir)
    output = data_dir / "teams_phase2.csv"
    teams.to_csv(output, index=False)
    print(f"Created {output} with {len(teams)} teams")
    print("\nConnector status:")
    print(connector_status(data_dir).to_string(index=False))


if __name__ == "__main__":
    main()
