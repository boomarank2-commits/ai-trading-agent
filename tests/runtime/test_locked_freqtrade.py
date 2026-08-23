from __future__ import annotations

import hashlib
import logging
import tempfile
import unittest
from pathlib import Path

from freqtrade.configuration import Configuration
from freqtrade.enums import RunMode
from freqtrade.resolvers.strategy_resolver import StrategyResolver
from starlette.websockets import WebSocketDisconnect
from uvicorn.protocols.utils import ClientDisconnected

from runtime.locked_freqtrade import (
    _ExpectedFreqUiDisconnectFilter,
    _install_exact_loader,
    _install_expected_frequi_disconnect_filter,
    _load_exact_strategy,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = (
    REPO_ROOT / "runtime" / "user_data" / "strategies" / "CompressionBreakout250.py"
)
CONFIG = REPO_ROOT / "runtime" / "user_data" / "config.json"
PUBLIC_OVERLAY = REPO_ROOT / "runtime" / "user_data" / "config-public.json"
LIVE_OVERLAY = REPO_ROOT / "runtime" / "user_data" / "config-live.example.json"
USER_DATA = REPO_ROOT / "runtime" / "user_data"


def _uvicorn_error_record(error: BaseException) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.error",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Exception in ASGI application",
        args=(),
        exc_info=(type(error), error, None),
    )


class ExpectedFreqUiDisconnectFilterTests(unittest.TestCase):
    def test_suppresses_only_expected_page_navigation_disconnects(self) -> None:
        expected_filter = _ExpectedFreqUiDisconnectFilter()

        try:
            raise ClientDisconnected()
        except ClientDisconnected:
            try:
                raise WebSocketDisconnect(code=1006)
            except WebSocketDisconnect as disconnect:
                expected = disconnect

        self.assertFalse(expected_filter.filter(_uvicorn_error_record(expected)))
        self.assertTrue(
            expected_filter.filter(_uvicorn_error_record(WebSocketDisconnect(code=1001)))
        )
        self.assertTrue(expected_filter.filter(_uvicorn_error_record(ValueError("real bug"))))

        other_message = _uvicorn_error_record(expected)
        other_message.msg = "Different Uvicorn failure"
        self.assertTrue(expected_filter.filter(other_message))

        other_logger = _uvicorn_error_record(expected)
        other_logger.name = "freqtrade.worker"
        self.assertTrue(expected_filter.filter(other_logger))

    def test_install_is_idempotent(self) -> None:
        logger = logging.getLogger("uvicorn.error")
        original_filters = list(logger.filters)
        try:
            logger.filters = []
            _install_expected_frequi_disconnect_filter()
            _install_expected_frequi_disconnect_filter()
            matching = [
                item
                for item in logger.filters
                if isinstance(item, _ExpectedFreqUiDisconnectFilter)
            ]
            self.assertEqual(len(matching), 1)
        finally:
            logger.filters = original_filters


class LockedStrategyLoaderTests(unittest.TestCase):
    def test_loads_only_exact_hash_pinned_source_bytes(self) -> None:
        digest = hashlib.sha256(STRATEGY.read_bytes()).hexdigest()
        strategy_type, source = _load_exact_strategy(
            STRATEGY, digest, "CompressionBreakout250"
        )
        self.assertEqual(strategy_type.__name__, "CompressionBreakout250")
        self.assertEqual(strategy_type.__authorized_source_sha256__, digest)
        self.assertIn("class CompressionBreakout250", source)

        with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
            _load_exact_strategy(STRATEGY, "0" * 64, "CompressionBreakout250")

    def test_competing_directory_file_cannot_change_exact_loaded_class(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authorized = root / "ZAuthorized.py"
            authorized.write_bytes(STRATEGY.read_bytes())
            (root / "AAA.py").write_text(
                "class CompressionBreakout250:\n    EVIL = True\n", encoding="utf-8"
            )
            (root / "CompressionBreakout250.json").write_text(
                '{"stoploss": -0.99}', encoding="utf-8"
            )
            digest = hashlib.sha256(authorized.read_bytes()).hexdigest()
            strategy_type, _source = _load_exact_strategy(
                authorized, digest, "CompressionBreakout250"
            )
            self.assertFalse(hasattr(strategy_type, "EVIL"))
            self.assertEqual(strategy_type.stoploss, -0.055)

    def test_freqtrade_resolver_receives_exact_in_memory_class_for_active_dryrun(self) -> None:
        digest = hashlib.sha256(STRATEGY.read_bytes()).hexdigest()
        strategy_type, source = _load_exact_strategy(
            STRATEGY, digest, "CompressionBreakout250"
        )
        original_loader = StrategyResolver._load_strategy
        try:
            _install_exact_loader(strategy_type, source, "CompressionBreakout250")
            config = Configuration(
                {
                    "config": [str(CONFIG), str(PUBLIC_OVERLAY)],
                    "strategy": "CompressionBreakout250",
                    "user_data_dir": str(USER_DATA),
                },
                RunMode.DRY_RUN,
            ).get_config()
            config["initial_state"] = "running"
            loaded = StrategyResolver.load_strategy(config)
            self.assertIs(type(loaded), strategy_type)
            self.assertEqual(type(loaded).__authorized_source_sha256__, digest)
            loaded.bot_start()
        finally:
            StrategyResolver._load_strategy = staticmethod(original_loader)

    def test_unpromoted_live_overlay_cannot_start_v12_17_adjustment_contract(self) -> None:
        digest = hashlib.sha256(STRATEGY.read_bytes()).hexdigest()
        strategy_type, source = _load_exact_strategy(
            STRATEGY, digest, "CompressionBreakout250"
        )
        original_loader = StrategyResolver._load_strategy
        try:
            _install_exact_loader(strategy_type, source, "CompressionBreakout250")
            config = Configuration(
                {
                    "config": [str(CONFIG), str(LIVE_OVERLAY)],
                    "strategy": "CompressionBreakout250",
                    "user_data_dir": str(USER_DATA),
                },
                RunMode.LIVE,
            ).get_config()
            loaded = StrategyResolver.load_strategy(config)
            with self.assertRaisesRegex(RuntimeError, "execution safety contract failed"):
                loaded.bot_start()
        finally:
            StrategyResolver._load_strategy = staticmethod(original_loader)


if __name__ == "__main__":
    unittest.main()
