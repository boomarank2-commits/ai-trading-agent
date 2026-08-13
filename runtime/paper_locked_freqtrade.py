"""Paper-test bootstrap with exact strategy loading and credential-safe API logs.

The live recovery path keeps using ``locked_freqtrade.py``. This paper-only
wrapper extends the same exact-source loader without changing a file held open
by an already running testbot.
"""

from __future__ import annotations

import contextlib
import ctypes
import errno
import importlib
import logging
import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path

from freqtrade.main import main as freqtrade_main

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_locked_module = importlib.import_module("runtime.locked_freqtrade")
_locked_main = _locked_module.main

_QUERY_SECRET = re.compile(
    r"([?&](?:token|access_token)=)[^&\s\"']+",
    flags=re.IGNORECASE,
)


@contextlib.contextmanager
def exclusive_child_lock(path: Path) -> Iterator[None]:
    """Hold the official paper-child lock until Freqtrade has fully exited.

    The PowerShell supervisor owns a separate instance lock.  This second lock
    intentionally lives in this Python child, so a force-killed supervisor
    cannot leave an unaccounted Freqtrade process behind and then admit a new
    official supervisor.  On Windows, ``CreateFileW`` with a zero share mode is
    the same mandatory sharing contract used by ``FileShare.None`` in the
    launcher.  The POSIX branch keeps local development/tests fail-safe too.
    """

    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        create_file.restype = wintypes.HANDLE
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL

        generic_read_write = 0x80000000 | 0x40000000
        open_always = 4
        normal_attributes = 0x00000080
        handle = create_file(
            str(resolved),
            generic_read_write,
            0,  # No sharing: equivalent to System.IO.FileShare.None.
            None,
            open_always,
            normal_attributes,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if handle == invalid_handle:
            error_code = ctypes.get_last_error()
            raise RuntimeError(
                f"official paper-child lock is already held: {resolved} "
                f"(Windows error {error_code})"
            ) from ctypes.WinError(error_code)
        try:
            yield
        finally:
            if not close_handle(handle):
                error_code = ctypes.get_last_error()
                logging.getLogger(__name__).error(
                    "Could not close paper-child lock %s (Windows error %s)",
                    resolved,
                    error_code,
                )
        return

    import fcntl  # pragma: no cover - Windows is the supported launcher OS.

    descriptor = os.open(resolved, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                raise RuntimeError(
                    f"official paper-child lock is already held: {resolved}"
                ) from exc
            raise
        yield
    finally:
        os.close(descriptor)


def _extract_child_lock(arguments: list[str]) -> tuple[Path, list[str]]:
    """Remove the mandatory paper-only lock argument before locked dispatch."""

    try:
        separator = arguments.index("--")
    except ValueError as exc:
        raise RuntimeError("paper runtime requires the locked argument separator") from exc
    positions = [
        index
        for index, argument in enumerate(arguments[:separator])
        if argument == "--child-lock-file"
    ]
    if len(positions) != 1:
        raise RuntimeError("paper runtime requires exactly one --child-lock-file")
    position = positions[0]
    if position + 1 >= separator:
        raise RuntimeError("--child-lock-file requires an absolute path")
    lock_path = Path(arguments[position + 1])
    if not lock_path.is_absolute():
        raise RuntimeError("--child-lock-file must be absolute")
    forwarded = arguments[:position] + arguments[position + 2 :]
    return lock_path, forwarded


class UvicornQuerySecretFilter(logging.Filter):
    """Redact auth query values while retaining useful API diagnostics."""

    def filter(self, record: logging.LogRecord) -> bool:
        rendered = record.getMessage()
        redacted = _QUERY_SECRET.sub(r"\1[REDACTED]", rendered)
        if redacted != rendered:
            record.msg = redacted
            record.args = ()
        return True


def install_api_log_redaction() -> None:
    redactor = UvicornQuerySecretFilter()
    # Uvicorn logs WebSocket query strings on uvicorn.error even when HTTP
    # access_log is disabled. Do not hide errors; redact only credential values.
    for logger_name in ("uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).addFilter(redactor)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    child_lock_path, forwarded_arguments = _extract_child_lock(arguments)
    original_main = freqtrade_main

    def redacted_main(arguments: list[str]) -> int:
        install_api_log_redaction()
        return original_main(arguments)

    # Reuse the audited argument/hash/loader validation from locked_freqtrade
    # and replace only its imported main function for this call.
    with exclusive_child_lock(child_lock_path):
        previous = _locked_module.freqtrade_main
        try:
            _locked_module.freqtrade_main = redacted_main
            return _locked_main(forwarded_arguments)
        finally:
            _locked_module.freqtrade_main = previous


if __name__ == "__main__":
    raise SystemExit(main())
