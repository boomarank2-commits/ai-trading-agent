"""Locked Freqtrade entrypoint for the Testbot backtest.

The backtest must evaluate the exact strategy source used by the paper bot.
This wrapper reuses the audited exact-source loader from ``locked_freqtrade``
but permits only Freqtrade's ``backtesting`` command. It never starts live
trading and never loads exchange credentials.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from freqtrade.main import main as freqtrade_main

# Executed directly from the runtime directory, therefore import the sibling
# module without the package prefix.
from locked_freqtrade import _install_exact_loader, _load_exact_strategy


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
        or any(ch not in "0123456789abcdef" for ch in args.strategy_sha256)
    ):
        raise RuntimeError("strategy SHA-256 must be 64 lowercase hexadecimal characters")

    freqtrade_args = list(args.freqtrade_args)
    if freqtrade_args and freqtrade_args[0] == "--":
        freqtrade_args.pop(0)
    if not freqtrade_args or freqtrade_args[0] != "backtesting":
        raise RuntimeError("locked backtest runtime only permits the Freqtrade backtesting command")
    forbidden = {"--strategy-path", "--recursive-strategy-search", "--strategy-list"}
    if any(argument in forbidden for argument in freqtrade_args):
        raise RuntimeError("strategy search/list arguments are forbidden")

    strategy_type, source_text = _load_exact_strategy(
        args.strategy_source,
        args.strategy_sha256,
        args.strategy_class,
    )
    _install_exact_loader(strategy_type, source_text, args.strategy_class)
    freqtrade_main(freqtrade_args)
    return 0  # pragma: no cover - freqtrade_main exits


if __name__ == "__main__":
    raise SystemExit(main())
