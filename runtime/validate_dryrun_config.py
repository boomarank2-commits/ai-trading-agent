"""Validate the resolved Freqtrade configuration used by STARTBOT.bat."""

from __future__ import annotations

import argparse
import ast
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

EXPECTED_PAIRS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "BNB/USDT",
    "DOGE/USDT",
    "LINK/USDT",
    "TRX/USDT",
    "LTC/USDT",
    "BCH/USDT",
]


def _exact(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ValueError(f"{label} must be exactly {expected!r}, got {actual!r}")


def validate_strategy_directory(strategy_directory: Path) -> dict[str, Any]:
    """Ensure Freqtrade resolves only the authoritative branch strategy source."""
    strategy_directory = strategy_directory.resolve(strict=True)
    expected_source = strategy_directory / "CompressionBreakout250.py"
    if not expected_source.is_file():
        raise ValueError(f"required strategy source is missing: {expected_source}")
    if expected_source.with_suffix(".json").exists():
        raise ValueError("adjacent strategy parameter JSON is forbidden")

    definitions: list[str] = []
    for source in sorted(strategy_directory.glob("*.py")):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (OSError, UnicodeDecodeError, SyntaxError) as error:
            raise ValueError(f"strategy source is not valid UTF-8 Python: {source}") from error
        if any(
            isinstance(node, ast.ClassDef) and node.name == "CompressionBreakout250"
            for node in tree.body
        ):
            definitions.append(str(source.resolve()))
    _exact("CompressionBreakout250 definitions", definitions, [str(expected_source.resolve())])
    return {"strategy_source": str(expected_source.resolve())}


def validate(config: Mapping[str, Any]) -> dict[str, Any]:
    """Fail unless the effective STARTBOT configuration matches HIXTON-V1."""
    exact_values = {
        "dry_run": True,
        "initial_state": "running",
        "trading_mode": "spot",
        "margin_mode": "",
        "stake_currency": "USDT",
        "stake_amount": 80,
        "available_capital": 250,
        "dry_run_wallet": 250,
        "max_open_trades": 3,
        "position_adjustment_enable": False,
        "max_entry_position_adjustment": 0,
        "force_entry_enable": False,
        "cancel_open_orders_on_exit": True,
        "strategy": "CompressionBreakout250",
        "timeframe": "15m",
        "stoploss": -0.99,
        "db_url": "sqlite:///user_data/tradesv8.dryrun.sqlite",
    }
    for key, expected in exact_values.items():
        _exact(key, config.get(key), expected)
    _exact("minimal_roi", config.get("minimal_roi"), {})
    _exact("trailing_stop", config.get("trailing_stop"), False)
    _exact("use_exit_signal", config.get("use_exit_signal"), True)
    _exact("exit_profit_only", config.get("exit_profit_only"), False)
    if not math.isclose(
        float(config["stake_amount"]) * int(config["max_open_trades"]),
        240.0,
        abs_tol=1e-12,
    ):
        raise ValueError("maximum configured exposure must be exactly 240 USDT")

    exchange = config.get("exchange")
    if not isinstance(exchange, Mapping):
        raise ValueError("exchange must be an object")
    _exact("exchange.name", exchange.get("name"), "binance")
    _exact("exchange.enable_ws", exchange.get("enable_ws"), False)
    _exact("exchange.pair_whitelist", exchange.get("pair_whitelist"), EXPECTED_PAIRS)
    _exact("exchange.pair_blacklist", exchange.get("pair_blacklist"), [])
    for secret_name in ("key", "secret", "password", "uid"):
        if exchange.get(secret_name):
            raise ValueError(f"exchange.{secret_name} must not be configured in dry-run")
    for section in ("ccxt_config", "ccxt_async_config"):
        section_value = exchange.get(section)
        if not isinstance(section_value, Mapping):
            raise ValueError(f"exchange.{section} must be an object")
        _exact(f"exchange.{section}.apiKey", section_value.get("apiKey"), None)
        for secret_name in ("secret", "password", "uid"):
            if section_value.get(secret_name):
                raise ValueError(f"exchange.{section}.{secret_name} must not be configured in dry-run")
        options = section_value.get("options")
        if not isinstance(options, Mapping):
            raise ValueError(f"exchange.{section}.options must be an object")
        _exact(f"exchange.{section}.options.defaultType", options.get("defaultType"), "spot")

    _exact("pairlists", config.get("pairlists"), [{"method": "StaticPairList"}])

    api_server = config.get("api_server")
    if not isinstance(api_server, Mapping):
        raise ValueError("api_server must be an object")
    _exact("api_server.enabled", api_server.get("enabled"), True)
    _exact("api_server.listen_ip_address", api_server.get("listen_ip_address"), "127.0.0.1")
    _exact("api_server.listen_port", api_server.get("listen_port"), 8080)
    _exact("api_server.enable_openapi", api_server.get("enable_openapi"), False)
    _exact("api_server.CORS_origins", api_server.get("CORS_origins"), [])

    _exact("telegram.enabled", config.get("telegram", {}).get("enabled"), False)
    _exact("external_message_consumer.enabled", config.get("external_message_consumer", {}).get("enabled", False), False)
    _exact("webhook.enabled", config.get("webhook", {}).get("enabled", False), False)
    for key in ("strategy_path", "recursive_strategy_search", "add_config_files"):
        _exact(key, config.get(key), None)

    order_types = config.get("order_types")
    if not isinstance(order_types, Mapping):
        raise ValueError("order_types must be an object")
    for key, expected in {
        "entry": "limit",
        "exit": "limit",
        "force_exit": "market",
        "emergency_exit": "market",
        "stoploss": "limit",
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_interval": 60,
        "stoploss_on_exchange_limit_ratio": 0.99,
    }.items():
        _exact(f"order_types.{key}", order_types.get(key), expected)
    _exact("order_time_in_force", config.get("order_time_in_force"), {"entry": "GTC", "exit": "GTC"})
    _exact(
        "unfilledtimeout",
        config.get("unfilledtimeout"),
        {"entry": 5, "exit": 5, "exit_timeout_count": 2, "unit": "minutes"},
    )

    return {
        "ok": True,
        "mode": "dry_run_running",
        "strategy_family": "HIXTON-V1",
        "capital_usdt": 250,
        "stake_per_trade_usdt": 80,
        "maximum_exposure_usdt": 240,
        "max_open_positions": 3,
        "max_entries_per_pair": 1,
        "pairs": EXPECTED_PAIRS,
    }


def _load_stdin() -> Mapping[str, Any]:
    value = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    if not isinstance(value, Mapping):
        raise ValueError("effective configuration must be a JSON object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strategy-directory", type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        result = {
            **validate(_load_stdin()),
            **validate_strategy_directory(arguments.strategy_directory),
        }
        encoded = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
        if arguments.output is not None:
            arguments.output.write_text(encoded, encoding="utf-8", newline="\n")
        sys.stdout.write(encoded)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
