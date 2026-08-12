"""Generate deterministic registration metadata for an audited live candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from runtime.validate_runtime import validate


def generate(strategy: Path, strategy_name: str, repository: Path) -> dict[str, object]:
    runtime = repository / "runtime"
    result = validate(
        runtime / "user_data" / "config.json",
        runtime / "user_data" / "config-live.example.json",
        strategy,
        strategy_name=strategy_name,
        lock_path=repository / "uv.lock",
    )
    return {
        "artifact_sha256": result["strategy_sha256"],
        "artifact_size": strategy.resolve(strict=True).stat().st_size,
        "strategy": strategy_name,
        "metadata": {
            "deployment_manifest": {
                "config_sha256": result["effective_config_sha256"],
                "lock_sha256": result["dependency_lock_sha256"],
                "imports_sha256": result["local_imports_sha256"],
                "freqtrade_version": result["freqtrade_version"],
            }
        },
        "warning": (
            "Generation verifies the runtime contract but is not a source audit, "
            "promotion, or permission to trade."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", type=Path, required=True)
    parser.add_argument("--strategy-name", required=True)
    parser.add_argument(
        "--repository", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    payload = generate(args.strategy, args.strategy_name, args.repository.resolve())
    print(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
