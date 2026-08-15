from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "runtime" / "scripts"


def test_double_click_launchers_are_explicitly_test_only() -> None:
    start = (REPO_ROOT / "STARTBOT.bat").read_text(encoding="utf-8")
    stop = (REPO_ROOT / "STOP_NEUE_TESTTRADES.bat").read_text(encoding="utf-8")
    resume = (REPO_ROOT / "TESTTRADES_FREIGEBEN.bat").read_text(encoding="utf-8")
    report = (REPO_ROOT / "TESTBOT_AUSWERTUNG.bat").read_text(encoding="utf-8")

    assert "start-testbot-24x7.ps1" in start
    assert "DRY-RUN" in start
    assert "250 USDT" in start
    assert "where uv.exe" in start
    assert "winget install --id=astral-sh.uv -e" in start
    assert "config-live" not in start
    assert "start-live" not in start
    assert "DRYRUN_STOP_ENTRIES" in stop
    assert "STOP_ENTRIES" in stop
    assert "DRYRUN_STOP_ENTRIES" in resume
    assert "export-dryrun-report.ps1" in report


def test_supervisor_contract_is_fail_safe_and_persistent() -> None:
    source = (SCRIPTS / "start-testbot-24x7.ps1").read_text(encoding="utf-8")

    assert 'FREQTRADE__DRY_RUN = "true"' in source
    assert 'FREQTRADE__INITIAL_STATE = "running"' in source
    assert "DRYRUN_STOP_ENTRIES" in source
    assert '"--db-url", $databaseUrl' in source
    assert "tradesv8.dryrun.sqlite" in source
    assert "FileShare]::None" in source
    assert "SetThreadExecutionState" in source
    assert "2147483649" in source
    assert "2147483648" in source
    assert "setup-venv.ps1" in source
    assert "validate_dryrun_config.py" in source
    assert "locked_freqtrade.py" in source
    assert '"--strategy-sha256", $manifest.strategy.sha256' in source
    assert "show-config" in source
    assert "effectiveSettings.capital_usdt" in source
    assert "$environmentAllowlist" in source
    assert "$environmentWasMinimized = $true" in source
    assert "$savedEnvironment" in source
    assert "-SessionStartUtc" in source
    assert "-SessionEndUtc" in source
    assert "started_at_utc" in source
    assert "ended_at_utc" in source
    assert "Get-LowerSha256" in source
    assert "$configLock" in source
    assert "$publicOverlayLock" in source
    assert "$dependencyLock" in source
    assert "freqtrade.log" in source
    assert "dryrun-report-$sessionId.json" in source
    assert "@(0, 130, -1073741510)" in source
    assert "config-live" not in source
    assert "FREQTRADE__EXCHANGE__KEY" not in source
    assert "FREQTRADE__EXCHANGE__SECRET" not in source


def test_legacy_direct_entry_path_cannot_bypass_startbot_lock() -> None:
    legacy = (SCRIPTS / "start-dryrun.ps1").read_text(encoding="utf-8")
    assert "if ($EnableEntries)" in legacy
    assert "ausschliesslich STARTBOT.bat verwenden" in legacy


def test_manifest_atomic_writer_replaces_existing_target_under_windows_powershell(
    tmp_path: Path,
) -> None:
    """Execute the actual launcher function twice without running the bot."""
    target = tmp_path / "session-manifest.json"
    environment = os.environ.copy()
    environment.update(
        {
            "TEST_LAUNCHER_SOURCE": str(SCRIPTS / "start-testbot-24x7.ps1"),
            "TEST_MANIFEST_TARGET": str(target),
        }
    )
    script = r"""
$ErrorActionPreference = "Stop"
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $env:TEST_LAUNCHER_SOURCE,
    [ref]$tokens,
    [ref]$parseErrors
)
if ($parseErrors.Count -ne 0) {
    throw ($parseErrors | Out-String)
}
$functionAst = $ast.Find(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -eq "Write-JsonAtomic"
    },
    $true
)
if ($null -eq $functionAst) {
    throw "Write-JsonAtomic function not found"
}
Invoke-Expression $functionAst.Extent.Text
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
Write-JsonAtomic -Path $env:TEST_MANIFEST_TARGET -Value ([ordered]@{ write = 1 })
Write-JsonAtomic -Path $env:TEST_MANIFEST_TARGET -Value ([ordered]@{
    write = 2
    replacement_succeeded = $true
})
"""
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "write": 2,
        "replacement_succeeded": True,
    }
    assert list(tmp_path.glob(".session-manifest.json.*")) == []


def test_powershell_exporter_is_thin_read_only_python_wrapper(tmp_path: Path) -> None:
    session_id = "launcher-contract-test"
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPTS / "export-dryrun-report.ps1"),
            "-OutputDirectory",
            str(tmp_path),
            "-SessionId",
            session_id,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr

    output_json = tmp_path / f"dryrun-report-{session_id}.json"
    output_markdown = tmp_path / f"dryrun-report-{session_id}.md"
    assert output_json.is_file()
    assert output_markdown.is_file()

    wrapper = (SCRIPTS / "export-dryrun-report.ps1").read_text(encoding="utf-8")
    assert "export_dryrun_report.py" in wrapper
    assert 'Join-Path $repoRoot ".venv\\Scripts\\python.exe"' in wrapper
    assert 'pythonCommand = "py"' not in wrapper
    assert 'pythonCommand = "python"' not in wrapper
    assert "show-trades" not in wrapper
    assert "SELECT " not in wrapper
