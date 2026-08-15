"""Start Freqtrade with one already-opened-and-hashed strategy artifact.

The regular resolver searches directories and may load an adjacent parameter
JSON.  The live launcher uses this small trusted bootstrap instead: it reads
the exact registry-authorized source, verifies its digest, compiles those
bytes in memory, and replaces only Freqtrade's strategy-loading hook.  No
strategy directory is searched and no parameter sidecar is consulted.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import types
from pathlib import Path
from typing import Any

from freqtrade.main import main as freqtrade_main
from freqtrade.resolvers.strategy_resolver import StrategyResolver
from freqtrade.strategy.interface import IStrategy


def _stable_read(path: Path) -> bytes:
    resolved = path.resolve(strict=True)
    with resolved.open("rb") as stream:
        before = os.fstat(stream.fileno())
        source = stream.read()
        after_handle = os.fstat(stream.fileno())
    after_path = resolved.stat()

    def identity(stat: os.stat_result) -> tuple[int, int, int, int]:
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)

    if not identity(before) == identity(after_handle) == identity(after_path):
        raise RuntimeError(f"strategy changed while being read: {resolved}")
    return source


def _load_exact_strategy(
    source_path: Path,
    expected_sha256: str,
    class_name: str,
) -> tuple[type[IStrategy], str]:
    source = _stable_read(source_path)
    digest = hashlib.sha256(source).hexdigest()
    if digest != expected_sha256:
        raise RuntimeError(
            f"authorized strategy SHA-256 mismatch: expected {expected_sha256}, got {digest}"
        )
    try:
        source_text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("authorized strategy is not valid UTF-8") from exc

    module_name = f"_local_trader_authorized_{digest}"
    module = types.ModuleType(module_name)
    module.__file__ = str(source_path)
    module.__package__ = ""
    code = compile(source_text, str(source_path), "exec", dont_inherit=True)
    # Register for normal inspection/tracebacks, then execute only the exact bytes.
    sys.modules[module_name] = module
    exec(code, module.__dict__)
    candidate = module.__dict__.get(class_name)
    if not isinstance(candidate, type) or not issubclass(candidate, IStrategy):
        raise RuntimeError(
            f"authorized source does not define IStrategy subclass {class_name!r}"
        )
    if candidate.__module__ != module_name:
        raise RuntimeError("authorized strategy class was imported instead of defined locally")
    candidate.__file__ = str(source_path)
    candidate.__source__ = source_text
    candidate.__authorized_source_sha256__ = digest
    return candidate, source_text


def _install_exact_loader(
    strategy_type: type[IStrategy], source_text: str, expected_class: str
) -> None:
    original_validate = StrategyResolver.validate_strategy

    def exact_loader(
        strategy_name: str, config: dict[str, Any], extra_dir: str | None = None
    ) -> IStrategy:
        del extra_dir
        if strategy_name != expected_class:
            raise RuntimeError(
                f"runtime requested {strategy_name!r}, not authorized class {expected_class!r}"
            )
        instance = strategy_type(config=config)

        # StrategyResolver.load_strategy normally loads <Strategy>.json after this
        # hook returns.  Bind a no-op on this exact instance so no unregistered
        # sidecar can alter the audited artifact.
        instance.ft_set_special_params_from_file = types.MethodType(
            lambda _self: None, instance
        )
        strategy_type.__source__ = source_text
        return original_validate(instance)

    StrategyResolver._load_strategy = staticmethod(exact_loader)


def _install_testbot_api_routes() -> None:
    """Expose repository-owned Backtest routes only in paper/dry-run mode."""
    from freqtrade.rpc.api_server.webserver import ApiServer

    from runtime.testbot_backtest_api import build_router

    marker = "__daviddtech_testbot_backtest_installed__"
    current = ApiServer.configure_app
    if bool(getattr(current, marker, False)):
        return
    router = build_router()

    def configure_with_backtest(self: Any, app: Any, config: dict[str, Any]) -> Any:
        # Register before FreqUI's SPA catch-all route.
        app.include_router(router)
        return current(self, app, config)

    setattr(configure_with_backtest, marker, True)
    ApiServer.configure_app = configure_with_backtest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy-source", type=Path, required=True)
    parser.add_argument("--strategy-sha256", required=True)
    parser.add_argument("--strategy-class", required=True)
    parser.add_argument("freqtrade_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if not args.strategy_class.isidentifier():
        raise RuntimeError("strategy class must be a Python identifier")
    if (
        len(args.strategy_sha256) != 64
        or args.strategy_sha256 != args.strategy_sha256.lower()
        or any(character not in "0123456789abcdef" for character in args.strategy_sha256)
    ):
        raise RuntimeError("strategy SHA-256 must be 64 lowercase hexadecimal characters")
    freqtrade_args = list(args.freqtrade_args)
    if freqtrade_args and freqtrade_args[0] == "--":
        freqtrade_args.pop(0)
    if not freqtrade_args or freqtrade_args[0] != "trade":
        raise RuntimeError("locked runtime only permits the Freqtrade trade command")
    forbidden = {"--strategy-path", "--recursive-strategy-search"}
    if any(argument in forbidden for argument in freqtrade_args):
        raise RuntimeError("strategy search-path arguments are forbidden")

    strategy_type, source_text = _load_exact_strategy(
        args.strategy_source, args.strategy_sha256, args.strategy_class
    )
    _install_exact_loader(strategy_type, source_text, args.strategy_class)

    # STARTBOT sets this process-only value to true. The paused live launcher
    # does not receive the Backtest endpoints or UI extension.
    if os.environ.get("FREQTRADE__DRY_RUN", "").strip().lower() == "true":
        _install_testbot_api_routes()

    freqtrade_main(freqtrade_args)
    return 0  # pragma: no cover - freqtrade_main exits


if __name__ == "__main__":
    raise SystemExit(main())
