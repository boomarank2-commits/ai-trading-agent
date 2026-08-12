"""Fail-closed validation of one frozen Freqtrade execution bundle."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import math
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

EXPECTED_PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
EXPECTED_FREQTRADE_VERSION = "2026.7"
EMPTY_IMPORTS_SHA256 = hashlib.sha256(b"").hexdigest()
HASH_LENGTH = 64


def _stable_read(path: Path) -> bytes:
    resolved = path.resolve(strict=True)
    with resolved.open("rb") as stream:
        before = os.fstat(stream.fileno())
        content = stream.read()
        after_handle = os.fstat(stream.fileno())
    after_path = resolved.stat()

    def identity(stat: os.stat_result) -> tuple[int, int, int, int]:
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)

    if not identity(before) == identity(after_handle) == identity(after_path):
        raise ValueError(f"file changed while it was being read: {resolved}")
    return content


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _expected_hash(label: str, value: str | None) -> str | None:
    if value is None:
        return None
    if (
        len(value) != HASH_LENGTH
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return value


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_stable_read(path).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"configuration must be valid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"configuration must be an object: {path}")
    return value


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    output = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(output.get(key), dict):
            output[key] = _merge(output[key], value)
        else:
            output[key] = value
    return output


def _exact(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ValueError(f"{label} must be exactly {expected!r}, got {actual!r}")


def _literal_assignment(strategy_class: ast.ClassDef, name: str) -> Any:
    for node in strategy_class.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            try:
                return ast.literal_eval(value)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"strategy safety assignment {name} must be a literal"
                ) from exc
    raise ValueError(f"strategy safety assignment {name} is required")


def _base_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _strategy_contract(
    source_path: Path, source: bytes, strategy_name: str
) -> dict[str, float]:
    try:
        text = source.decode("utf-8")
        tree = ast.parse(text, filename=str(source_path))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise ValueError("strategy must be valid UTF-8 Python") from exc

    matching = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == strategy_name
    ]
    if len(matching) != 1:
        raise ValueError(
            f"strategy file must define exactly one top-level {strategy_name} class"
        )
    strategy_class = matching[0]
    if not any(_base_name(base) == "IStrategy" for base in strategy_class.bases):
        raise ValueError(f"{strategy_name} must directly inherit IStrategy")

    methods = {
        node.name
        for node in strategy_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    required_methods = {
        "bot_start",
        "confirm_trade_entry",
        "custom_stake_amount",
        "populate_entry_trend",
        "populate_exit_trend",
        "populate_indicators",
    }
    missing = sorted(required_methods - methods)
    if missing:
        raise ValueError(
            "strategy is missing fail-closed runtime/signal methods: "
            + ", ".join(missing)
        )

    expected_literals = {
        "can_short": False,
        "position_adjustment_enable": False,
        "max_entry_position_adjustment": 0,
        "timeframe": "15m",
        "stoploss": -0.055,
        "MAX_STAKE_USDT": 80.0,
        "MAX_TOTAL_CAPITAL_USDT": 250.0,
        "MAX_TOTAL_EXPOSURE_USDT": 240.0,
        "MAX_OPEN_POSITIONS": 3,
        "MAX_DAILY_LOSS_USDT": 10.0,
    }
    for name, expected in expected_literals.items():
        _exact(f"strategy.{name}", _literal_assignment(strategy_class, name), expected)

    order_types = _literal_assignment(strategy_class, "order_types")
    if not isinstance(order_types, dict):
        raise ValueError("strategy.order_types must be a literal object")
    for key, expected in {
        "entry": "limit",
        "exit": "limit",
        "force_exit": "market",
        "emergency_exit": "market",
        "stoploss": "limit",
        "stoploss_on_exchange": True,
        "stoploss_on_exchange_limit_ratio": 0.99,
    }.items():
        _exact(f"strategy.order_types.{key}", order_types.get(key), expected)

    time_in_force = _literal_assignment(strategy_class, "order_time_in_force")
    _exact("strategy.order_time_in_force", time_in_force, {"entry": "GTC", "exit": "GTC"})

    local_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                local_imports.append("relative import")
                continue
            roots = [] if node.module is None else [node.module.split(".", 1)[0]]
        elif isinstance(node, ast.Import):
            roots = [alias.name.split(".", 1)[0] for alias in node.names]
        else:
            continue
        for root in roots:
            if (source_path.parent / f"{root}.py").exists() or (
                source_path.parent / root
            ).is_dir():
                local_imports.append(root)
    if local_imports:
        raise ValueError(
            "single-file live strategies may not use local or relative imports: "
            + ", ".join(sorted(set(local_imports)))
        )

    return {
        "max_capital": float(expected_literals["MAX_TOTAL_CAPITAL_USDT"]),
        "max_position": float(expected_literals["MAX_STAKE_USDT"]),
        "max_exposure": float(expected_literals["MAX_TOTAL_EXPOSURE_USDT"]),
        "max_open_positions": float(expected_literals["MAX_OPEN_POSITIONS"]),
        "max_daily_loss": float(expected_literals["MAX_DAILY_LOSS_USDT"]),
    }


def _validate_risk_policy(
    policy: Mapping[str, Any], config: Mapping[str, Any], strategy_caps: Mapping[str, float]
) -> None:
    fields = {
        "exchange",
        "market_type",
        "quote_asset",
        "max_capital",
        "max_position",
        "max_exposure",
        "max_open_positions",
        "leverage",
        "allow_shorts",
        "allow_dca",
        "allow_martingale",
        "max_daily_loss",
        "max_drawdown",
    }
    _exact("risk_policy fields", set(policy), fields)
    _exact("risk_policy.exchange", policy.get("exchange"), "BINANCE")
    _exact("risk_policy.market_type", policy.get("market_type"), "SPOT")
    _exact("risk_policy.quote_asset", policy.get("quote_asset"), "USDT")
    _exact("risk_policy.leverage", float(policy.get("leverage", 0.0)), 1.0)
    for flag in ("allow_shorts", "allow_dca", "allow_martingale"):
        _exact(f"risk_policy.{flag}", policy.get(flag), False)

    hard_caps = {
        "max_capital": 250.0,
        "max_position": 80.0,
        "max_exposure": 240.0,
        "max_open_positions": 3.0,
        "max_daily_loss": 10.0,
        "max_drawdown": 15.0,
    }
    numeric_policy: dict[str, float] = {}
    for name, hard_maximum in hard_caps.items():
        value = policy.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"risk_policy.{name} must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric) or not 0.0 < numeric <= hard_maximum:
            raise ValueError(
                f"risk_policy.{name} must be positive and at most {hard_maximum:g}"
            )
        numeric_policy[name] = numeric

    effective = {
        "max_capital": float(config["available_capital"]),
        "max_position": float(config["stake_amount"]),
        "max_exposure": float(config["stake_amount"])
        * float(config["max_open_trades"]),
        "max_open_positions": float(config["max_open_trades"]),
        "max_daily_loss": strategy_caps["max_daily_loss"],
    }
    for name, value in effective.items():
        if value > numeric_policy[name]:
            raise ValueError(
                f"effective {name} {value:g} exceeds authorized risk policy "
                f"{numeric_policy[name]:g}"
            )


def validate(
    config_path: Path,
    overlay_path: Path,
    strategy_path: Path,
    *,
    strategy_name: str = "CompressionBreakout250",
    expected_strategy_sha256: str | None = None,
    expected_config_sha256: str | None = None,
    lock_path: Path | None = None,
    expected_lock_sha256: str | None = None,
    expected_imports_sha256: str | None = None,
    expected_freqtrade_version: str = EXPECTED_FREQTRADE_VERSION,
    risk_policy: Mapping[str, Any] | None = None,
    effective_config_output: Path | None = None,
) -> dict[str, Any]:
    if not strategy_name.isidentifier():
        raise ValueError("strategy_name must be a Python identifier")
    config = _merge(
        _load(config_path.resolve(strict=True)),
        _load(overlay_path.resolve(strict=True)),
    )
    # This is the value the fixed launcher supplies through --strategy.
    config["strategy"] = strategy_name
    exchange = config.get("exchange", {})
    if not isinstance(exchange, dict):
        raise ValueError("exchange must be an object")

    invariants = {
        "dry_run": False,
        "initial_state": "paused",
        "trading_mode": "spot",
        "margin_mode": "",
        "stake_currency": "USDT",
        "stake_amount": 80,
        "available_capital": 250,
        "max_open_trades": 3,
        "position_adjustment_enable": False,
        "max_entry_position_adjustment": 0,
        "force_entry_enable": False,
        "cancel_open_orders_on_exit": False,
        "db_url": "sqlite:///user_data/tradesv3.live.sqlite",
    }
    for key, expected in invariants.items():
        _exact(key, config.get(key), expected)
    if not math.isclose(config["stake_amount"] * config["max_open_trades"], 240.0):
        raise ValueError("configured maximum exposure must be exactly 240 USDT")

    _exact("exchange.name", exchange.get("name"), "binance")
    _exact("exchange.pair_whitelist", exchange.get("pair_whitelist"), EXPECTED_PAIRS)
    _exact("exchange.pair_blacklist", exchange.get("pair_blacklist"), [])
    if exchange.get("key") or exchange.get("secret"):
        raise ValueError("exchange credentials must not be embedded in configuration files")
    _exact("pairlists", config.get("pairlists"), [{"method": "StaticPairList"}])
    for section in ("ccxt_config", "ccxt_async_config"):
        options = exchange.get(section, {}).get("options", {})
        _exact(f"exchange.{section}.options.defaultType", options.get("defaultType"), "spot")

    _exact("api_server.enabled", config.get("api_server", {}).get("enabled"), False)
    _exact("telegram.enabled", config.get("telegram", {}).get("enabled"), False)
    _exact(
        "external_message_consumer.enabled",
        config.get("external_message_consumer", {}).get("enabled", False),
        False,
    )
    _exact("webhook.enabled", config.get("webhook", {}).get("enabled", False), False)
    _exact("add_config_files", config.get("add_config_files"), None)
    _exact("strategy_path", config.get("strategy_path"), None)
    _exact("recursive_strategy_search", config.get("recursive_strategy_search"), None)
    _exact("strategy", config.get("strategy"), strategy_name)
    _exact("timeframe", config.get("timeframe"), "15m")
    _exact("stoploss", config.get("stoploss"), -0.055)
    _exact("order_types.entry", config.get("order_types", {}).get("entry"), "limit")
    _exact("order_types.exit", config.get("order_types", {}).get("exit"), "limit")
    _exact(
        "order_types.force_exit",
        config.get("order_types", {}).get("force_exit"),
        "market",
    )
    _exact(
        "order_types.emergency_exit",
        config.get("order_types", {}).get("emergency_exit"),
        "market",
    )
    _exact(
        "order_types.stoploss", config.get("order_types", {}).get("stoploss"), "limit"
    )
    _exact(
        "order_types.stoploss_on_exchange",
        config.get("order_types", {}).get("stoploss_on_exchange"),
        True,
    )
    _exact(
        "order_types.stoploss_on_exchange_limit_ratio",
        config.get("order_types", {}).get("stoploss_on_exchange_limit_ratio"),
        0.99,
    )
    if int(config.get("order_types", {}).get("stoploss_on_exchange_interval", 0)) < 60:
        raise ValueError("stoploss_on_exchange_interval must be at least 60 seconds")
    _exact(
        "order_time_in_force",
        config.get("order_time_in_force"),
        {"entry": "GTC", "exit": "GTC"},
    )
    _exact(
        "unfilledtimeout",
        config.get("unfilledtimeout"),
        {
            "entry": 5,
            "exit": 5,
            "exit_timeout_count": 2,
            "unit": "minutes",
        },
    )

    strategy = strategy_path.resolve(strict=True)
    if strategy.suffix.casefold() != ".py":
        raise ValueError("strategy artifact must be a .py file")
    parameter_file = strategy.with_suffix(".json")
    if parameter_file.exists():
        raise ValueError(f"unhashed adjacent strategy parameters are forbidden: {parameter_file}")
    strategy_bytes = _stable_read(strategy)
    strategy_digest = _sha256(strategy_bytes)
    required_strategy_hash = _expected_hash(
        "expected_strategy_sha256", expected_strategy_sha256
    )
    if required_strategy_hash is not None:
        _exact("strategy SHA-256", strategy_digest, required_strategy_hash)
    strategy_caps = _strategy_contract(strategy, strategy_bytes, strategy_name)

    canonical_config = json.dumps(
        config,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    config_digest = _sha256(canonical_config)
    required_config_hash = _expected_hash("expected_config_sha256", expected_config_sha256)
    if required_config_hash is not None:
        _exact("effective config SHA-256", config_digest, required_config_hash)

    required_imports_hash = _expected_hash(
        "expected_imports_sha256", expected_imports_sha256
    )
    if required_imports_hash is not None:
        _exact("local imports SHA-256", EMPTY_IMPORTS_SHA256, required_imports_hash)

    lock_digest: str | None = None
    if expected_lock_sha256 is not None and lock_path is None:
        raise ValueError("lock_path is required with expected_lock_sha256")
    if lock_path is not None:
        lock_digest = _sha256(_stable_read(lock_path))
        required_lock_hash = _expected_hash("expected_lock_sha256", expected_lock_sha256)
        if required_lock_hash is not None:
            _exact("dependency lock SHA-256", lock_digest, required_lock_hash)

    installed_freqtrade = importlib.metadata.version("freqtrade")
    _exact("installed Freqtrade version", installed_freqtrade, expected_freqtrade_version)

    if risk_policy is not None:
        _validate_risk_policy(risk_policy, config, strategy_caps)

    frozen_path: str | None = None
    if effective_config_output is not None:
        output = effective_config_output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(canonical_config)
            stream.flush()
            os.fsync(stream.fileno())
        if _sha256(_stable_read(output)) != config_digest:
            raise ValueError("frozen effective configuration failed its post-write hash check")
        frozen_path = str(output)

    return {
        "ok": True,
        "mode": "live_recovery_paused",
        "strategy": strategy_name,
        "strategy_path": str(strategy),
        "strategy_sha256": strategy_digest,
        "effective_config_sha256": config_digest,
        "effective_config_path": frozen_path,
        "dependency_lock_sha256": lock_digest,
        "local_imports_sha256": EMPTY_IMPORTS_SHA256,
        "freqtrade_version": installed_freqtrade,
        "maximum_exposure_usdt": 240,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--strategy", type=Path, required=True)
    parser.add_argument("--strategy-name", default="CompressionBreakout250")
    parser.add_argument("--expected-strategy-sha256")
    parser.add_argument("--expected-config-sha256")
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--expected-lock-sha256")
    parser.add_argument("--expected-imports-sha256")
    parser.add_argument(
        "--expected-freqtrade-version", default=EXPECTED_FREQTRADE_VERSION
    )
    parser.add_argument("--risk-policy-json")
    parser.add_argument("--write-effective-config", type=Path)
    args = parser.parse_args()
    policy: Mapping[str, Any] | None = None
    if args.risk_policy_json is not None:
        value = json.loads(args.risk_policy_json)
        if not isinstance(value, dict):
            raise ValueError("--risk-policy-json must be a JSON object")
        policy = value
    result = validate(
        args.config,
        args.overlay,
        args.strategy,
        strategy_name=args.strategy_name,
        expected_strategy_sha256=args.expected_strategy_sha256,
        expected_config_sha256=args.expected_config_sha256,
        lock_path=args.lock,
        expected_lock_sha256=args.expected_lock_sha256,
        expected_imports_sha256=args.expected_imports_sha256,
        expected_freqtrade_version=args.expected_freqtrade_version,
        risk_policy=policy,
        effective_config_output=args.write_effective_config,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
