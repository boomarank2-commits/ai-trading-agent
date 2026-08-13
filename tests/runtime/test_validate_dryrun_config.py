from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest

from runtime.validate_dryrun_config import validate, validate_strategy_directory

REPO_ROOT = Path(__file__).resolve().parents[2]


def _effective_config() -> dict:
    config = json.loads(
        (REPO_ROOT / "runtime" / "user_data" / "config.json").read_text(encoding="utf-8")
    )
    overlay = json.loads(
        (REPO_ROOT / "runtime" / "user_data" / "config-paper-public.json").read_text(
            encoding="utf-8"
        )
    )
    runtime_overlay = json.loads(
        (REPO_ROOT / "runtime" / "user_data" / "config-paper-runtime.json").read_text(
            encoding="utf-8"
        )
    )
    config["exchange"]["ccxt_config"].update(overlay["exchange"]["ccxt_config"])
    config["exchange"]["ccxt_async_config"].update(
        overlay["exchange"]["ccxt_async_config"]
    )
    config["api_server"].update(
        {
            "enabled": True,
            "username": "testbot",
            "password": "REDACTED",
            "jwt_secret_key": "j" * 64,
            "ws_token": "w" * 43,
        }
    )
    config.update(
        {
            key: value
            for key, value in runtime_overlay.items()
            if not key.startswith("$") and key != "_comment"
        }
    )
    config["initial_state"] = "running"
    return config


def test_known_dryrun_configuration_matches_displayed_contract() -> None:
    result = validate(_effective_config())
    assert result["ok"] is True
    assert result["maximum_exposure_usdt"] == 240
    assert result["strategy"] == "PaperTrendBreakout250V1"
    assert result["timeframe"] == "1h"
    assert result["paper_only"] is True


@pytest.mark.parametrize(
    ("path", "unsafe_value"),
    [
        (("dry_run",), False),
        (("available_capital",), 251),
        (("dry_run_wallet",), 100),
        (("stake_amount",), 81),
        (("max_open_trades",), 4),
        (("strategy",), "CompressionBreakout250"),
        (("timeframe",), "15m"),
        (("minimal_roi",), {"0": 0.05}),
        (("exchange", "pair_whitelist"), ["BTC/USDT"]),
        (("exchange", "ccxt_config", "apiKey"), "secret"),
        (("exchange", "ccxt_async_config", "secret"), "secret"),
        (("api_server", "enabled"), False),
        (("api_server", "listen_ip_address"), "0.0.0.0"),
        (("api_server", "listen_port"), 8081),
        (("api_server", "username"), "admin"),
        (("api_server", "password"), "not-redacted"),
        (("api_server", "jwt_secret_key"), "somethingRandomSomethingRandom123"),
        (("api_server", "ws_token"), "short"),
        (("strategy_path",), "other"),
    ],
)
def test_changed_effective_contract_fails_closed(
    path: tuple[str, ...], unsafe_value: object
) -> None:
    config = copy.deepcopy(_effective_config())
    target = config
    for part in path[:-1]:
        target = target.setdefault(part, {})
    target[path[-1]] = unsafe_value
    with pytest.raises(ValueError):
        validate(config)


def test_validator_accepts_real_freqtrade_show_config_output() -> None:
    script = """
$oldDry=$env:FREQTRADE__DRY_RUN
$oldState=$env:FREQTRADE__INITIAL_STATE
try {
  $env:FREQTRADE__DRY_RUN='true'
  $env:FREQTRADE__INITIAL_STATE='running'
  $env:FREQTRADE__API_SERVER__ENABLED='true'
  $env:FREQTRADE__API_SERVER__USERNAME='testbot'
  $env:FREQTRADE__API_SERVER__PASSWORD='valid-local-password'
  $env:FREQTRADE__API_SERVER__JWT_SECRET_KEY=('j' * 64)
  $env:FREQTRADE__API_SERVER__WS_TOKEN=('w' * 43)
  & '.\\.venv\\Scripts\\freqtrade.exe' show-config `
    --config '.\\runtime\\user_data\\config.json' `
    --config '.\\runtime\\user_data\\config-paper-public.json' `
    --config '.\\runtime\\user_data\\config-paper-runtime.json' `
    --userdir '.\\runtime\\user_data'
} finally {
  if ($null -eq $oldDry) {
    Remove-Item Env:FREQTRADE__DRY_RUN -ErrorAction SilentlyContinue
  } else {
    $env:FREQTRADE__DRY_RUN=$oldDry
  }
  if ($null -eq $oldState) {
    Remove-Item Env:FREQTRADE__INITIAL_STATE -ErrorAction SilentlyContinue
  } else {
    $env:FREQTRADE__INITIAL_STATE=$oldState
  }
  Get-ChildItem Env:FREQTRADE__API_SERVER__* | Remove-Item -ErrorAction SilentlyContinue
}
"""
    shown = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    config = json.loads(shown[shown.index("{") :])
    assert validate(config)["mode"] == "dry_run_running"


def test_strategy_directory_has_exactly_one_intended_definition() -> None:
    strategy_directory = REPO_ROOT / "runtime" / "user_data" / "strategies"
    result = validate_strategy_directory(strategy_directory)
    assert result["strategy_source"].endswith("PaperTrendBreakout250V1.py")


def test_cli_accepts_windows_powershell_bom_on_stdin() -> None:
    config = json.dumps(_effective_config(), separators=(",", ":"))
    validator = REPO_ROOT / "runtime" / "validate_dryrun_config.py"
    python = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    script = (
        f"$value = @'\n{config}\n'@; "
        f"$value | & '{python}' '{validator}' "
        f"--strategy-directory '{REPO_ROOT / 'runtime' / 'user_data' / 'strategies'}'"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["ok"] is True
