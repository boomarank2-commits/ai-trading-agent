"""Install the repository-owned Testbot UI hook into the installed FreqUI index.

FreqUI itself is downloaded by Freqtrade into .venv and is therefore not kept
in Git. This patch is intentionally tiny and idempotent: it only adds one
repository-served script tag. On every setup/start it verifies the hook, so a
fresh clone receives the Backtest navigation automatically after ``install-ui``.
"""

from __future__ import annotations

from pathlib import Path

import freqtrade

SCRIPT_TAG = '<script src="/testbot-backtest.js" defer></script>'


def main() -> int:
    index = (
        Path(freqtrade.__file__).resolve().parent
        / "rpc"
        / "api_server"
        / "ui"
        / "installed"
        / "index.html"
    )
    if not index.is_file():
        raise RuntimeError(f"FreqUI index not found: {index}")

    text = index.read_text(encoding="utf-8")
    if SCRIPT_TAG in text:
        print(f"Testbot Backtest UI hook already installed: {index}")
        return 0

    marker = "</body>"
    if marker not in text:
        raise RuntimeError("FreqUI index has no </body> marker; refusing unsafe patch")
    patched = text.replace(marker, f"{SCRIPT_TAG}{marker}", 1)
    index.write_text(patched, encoding="utf-8", newline="")
    verify = index.read_text(encoding="utf-8")
    if verify.count(SCRIPT_TAG) != 1:
        raise RuntimeError("Testbot Backtest UI hook verification failed")
    print(f"Installed Testbot Backtest UI hook: {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
