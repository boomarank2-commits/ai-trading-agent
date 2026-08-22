"""Locked Freqtrade entrypoint for the Testbot backtest.

The backtest must evaluate the exact strategy source used by the paper bot.
This wrapper reuses the audited exact-source loader from ``locked_freqtrade``
but permits only Freqtrade's ``backtesting`` command. It never starts live
trading and never loads exchange credentials.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from freqtrade.main import main as freqtrade_main

# Executed directly from the runtime directory, therefore import the sibling
# module without the package prefix.
try:
    from locked_freqtrade import _install_exact_loader, _load_exact_strategy
except ModuleNotFoundError:  # Package import used by unit tests.
    from runtime.locked_freqtrade import _install_exact_loader, _load_exact_strategy


class _FileAccessAudit:
    """Record Python-level file access without logging contents or environment values."""

    def __init__(self, output: Path, context: dict[str, Any]) -> None:
        self.output = output.resolve()
        self.context = context
        self.enabled = True
        self.files: dict[tuple[str, str], int] = {}
        self.processes: list[dict[str, str]] = []
        self.candles: dict[str, dict[str, Any]] = {}
        sys.addaudithook(self._hook)

    def _hook(self, event: str, args: tuple[Any, ...]) -> None:
        if not self.enabled:
            return
        if event == "open" and args:
            target = args[0]
            if isinstance(target, int):
                return
            try:
                path = Path(os.fsdecode(os.fspath(target))).resolve()
            except (OSError, TypeError, ValueError):
                return
            mode = str(args[1]) if len(args) > 1 else "unknown"
            key = (str(path), mode)
            self.files[key] = self.files.get(key, 0) + 1
        elif event == "subprocess.Popen":
            executable = str(args[0]) if args else "unknown"
            self.processes.append({"executable": executable})

    def record_candle_load(self, filename: Path, timeframe: str) -> None:
        """Record the exact file handed to Arrow before its native read begins."""

        resolved = filename.resolve()
        key = str(resolved)
        previous = self.candles.get(key)
        if previous is not None:
            previous["load_count"] += 1
            return
        with resolved.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        stat = resolved.stat()
        self.candles[key] = {
            "path": key,
            "timeframe": timeframe,
            "sha256_at_load": digest,
            "size_at_load": stat.st_size,
            "mtime_ns_at_load": stat.st_mtime_ns,
            "load_count": 1,
        }

    def write(self) -> None:
        self.enabled = False
        payload = {
            "schema_version": 1,
            "finished_at_utc": datetime.now(UTC).isoformat(),
            "process_id": os.getpid(),
            "working_directory": str(Path.cwd().resolve()),
            "context": self.context,
            "opened_files": [
                {"path": path, "mode": mode, "count": count}
                for (path, mode), count in sorted(self.files.items())
            ],
            "candle_loads": [self.candles[path] for path in sorted(self.candles)],
            "spawned_processes": self.processes,
        }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _install_candle_load_audit(audit: _FileAccessAudit) -> None:
    """Trace Arrow-backed candle loads at Freqtrade's filename boundary."""

    from freqtrade.data.history.datahandlers.arrowdatahandler import ArrowDataHandler

    original = ArrowDataHandler._load_ohlcv_dataframe

    def audited_load(
        handler: ArrowDataHandler,
        filename: Path,
        timeframe: str,
        timerange: Any,
    ) -> Any:
        audit.record_candle_load(filename, timeframe)
        return original(handler, filename, timeframe, timerange)

    ArrowDataHandler._load_ohlcv_dataframe = audited_load


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy-source", type=Path, required=True)
    parser.add_argument("--strategy-sha256", required=True)
    parser.add_argument("--strategy-class", required=True)
    parser.add_argument("--file-audit-output", type=Path)
    parser.add_argument("freqtrade_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    audit = (
        _FileAccessAudit(
            args.file_audit_output,
            {
                "strategy_source": str(args.strategy_source.resolve()),
                "strategy_sha256": args.strategy_sha256,
                "strategy_class": args.strategy_class,
                "freqtrade_command": list(args.freqtrade_args),
                "python_executable": str(Path(sys.executable).resolve()),
                "python_prefix": str(Path(sys.prefix).resolve()),
            },
        )
        if args.file_audit_output is not None
        else None
    )

    try:
        if not args.strategy_class.isidentifier():
            raise RuntimeError("strategy class must be a Python identifier")
        if (
            len(args.strategy_sha256) != 64
            or args.strategy_sha256 != args.strategy_sha256.lower()
            or any(ch not in "0123456789abcdef" for ch in args.strategy_sha256)
        ):
            raise RuntimeError("strategy SHA-256 must be 64 lowercase hexadecimal characters")

        freqtrade_args = list(args.freqtrade_args)
        if freqtrade_args and freqtrade_args[0] == "--":
            freqtrade_args.pop(0)
        if not freqtrade_args or freqtrade_args[0] != "backtesting":
            raise RuntimeError(
                "locked backtest runtime only permits the Freqtrade backtesting command"
            )
        forbidden = {"--strategy-path", "--recursive-strategy-search", "--strategy-list"}
        if any(argument in forbidden for argument in freqtrade_args):
            raise RuntimeError("strategy search/list arguments are forbidden")

        strategy_type, source_text = _load_exact_strategy(
            args.strategy_source,
            args.strategy_sha256,
            args.strategy_class,
        )
        _install_exact_loader(strategy_type, source_text, args.strategy_class)
        if audit is not None:
            _install_candle_load_audit(audit)
        freqtrade_main(freqtrade_args)
        return 0  # pragma: no cover - freqtrade_main exits
    finally:
        if audit is not None:
            audit.write()


if __name__ == "__main__":
    raise SystemExit(main())
