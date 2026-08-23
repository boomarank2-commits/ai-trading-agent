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
        (REPO_ROOT / "runtime" / "user_data" / "config-public.json").read_text(
            encoding="utf-8"
        )
    )
    config["exchange"]["ccxt_config"].update(overlay["exchange"]["ccxt_config"])
    config["exchange"]["ccxt_async_config"].update(
        overlay["exchange"]["ccxt_async_config"]
    )
    config["exchange"]["enable_ws"] = overlay["exchange"]["enable_ws"]
    config["api_server"].update(overlay["api_server"])
    config["initial_state"] = "running"
    return config


def test_known_dryrun_configuration_matches_displayed_contract() -> None:
    result = validate(_effective_config())
    assert result["ok"] is True
    assert result["maximum_exposure_usdt"] == 240


@pytest.mark.parametrize(
    ("path", "unsafe_value"),
    [
        (("dry_run",), False),
        (("available_capital",), 251),
        (("dry_run_wallet",), 100),
        (("stake_amount",), 81),
        (("max_open_trades",), 4),
        (("minimal_roi",), {"0": 0.05}),
        (("trailing_stop",), True),
        (("db_url",), "sqlite:///user_data/tradesv3.dryrun.sqlite"),
        (("exchange", "pair_whitelist"), ["BTC/USDT"]),
        (("exchange", "enable_ws"), True),
        (("exchange", "ccxt_config", "apiKey"), "secret"),
        (("exchange", "ccxt_async_config", "secret"), "secret"),
        (("api_server", "enabled"), False),
        (("api_server", "listen_ip_address"), "0.0.0.0"),
        (("api_server", "listen_port"), 8081),
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
  & '.\\.venv\\Scripts\\freqtrade.exe' show-config `
    --config '.\\runtime\\user_data\\config.json' `
    --config '.\\runtime\\user_data\\config-public.json' `
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
    assert result["strategy_source"].endswith("CompressionBreakout250.py")


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
