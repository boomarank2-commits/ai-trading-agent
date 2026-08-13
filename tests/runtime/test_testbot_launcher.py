from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "runtime" / "scripts"


def test_double_click_launchers_are_explicitly_test_only() -> None:
    start = (REPO_ROOT / "STARTBOT.bat").read_text(encoding="utf-8")
    stop = (REPO_ROOT / "STOP_NEUE_TESTTRADES.bat").read_text(encoding="utf-8")
    resume = (REPO_ROOT / "TESTTRADES_FREIGEBEN.bat").read_text(encoding="utf-8")
    report = (REPO_ROOT / "TESTBOT_AUSWERTUNG.bat").read_text(encoding="utf-8")

    assert "manage-testbot-ui-auth.ps1" in start
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
    assert "tradesv3.paper-trend-breakout-250-v1.sqlite" in source
    assert "FileShare]::None" in source
    assert 'childLockPath = Join-Path $logsRoot "testbot-child.lock"' in source
    assert '"--child-lock-file", ([System.IO.Path]::GetFullPath($childLockPath))' in source
    assert source.index("$instanceLock = [System.IO.File]::Open(") < source.index(
        "$childLockReservation = [System.IO.File]::Open("
    ) < source.index("    Repair-InterruptedSessionManifests `")
    assert source.index("$childLockReservation.Dispose()") < source.index(
        "& $pythonExe @commandArgs"
    )
    assert "SetThreadExecutionState" in source
    assert "2147483649" in source
    assert "2147483648" in source
    assert "setup-venv.ps1" in source
    assert "validate_dryrun_config.py" in source
    assert "locked_freqtrade.py" in source
    assert '"--strategy-sha256", $manifest.strategy.sha256' in source
    assert "show-config" in source
    assert "effectiveSettings.capital_usdt" in source
    assert "Enter-TestbotChildEnvironment" in source
    assert "$environmentWasMinimized = $true" in source
    assert "$savedEnvironment" in source
    assert "Repair-InterruptedSessionManifests" in source
    assert 'status = "interrupted"' in source
    assert "created_after_interruption" in source
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
    assert 'paperStrategyName = "PaperTrendBreakout250V1"' in source
    assert 'paperStrategyVersion = 1' in source
    assert "config-paper-runtime.json" in source
    assert '"--config", $paperRuntimeOverlayPath' in source
    assert '"--strategy-class", $paperStrategyName' in source
    assert '"--strategy", $paperStrategyName' in source
    assert "paper_runtime_overlay_sha256" in source
    assert "paper_only = $true" in source
    assert "FREQTRADE__EXCHANGE__KEY" not in source
    assert "FREQTRADE__EXCHANGE__SECRET" not in source


def test_paper_overlay_is_isolated_from_baseline_and_live_launchers() -> None:
    base = json.loads(
        (REPO_ROOT / "runtime" / "user_data" / "config.json").read_text(
            encoding="utf-8"
        )
    )
    paper = json.loads(
        (REPO_ROOT / "runtime" / "user_data" / "config-paper-runtime.json").read_text(
            encoding="utf-8"
        )
    )
    assert base["strategy"] == "CompressionBreakout250"
    assert base["timeframe"] == "15m"
    assert paper["strategy"] == "PaperTrendBreakout250V1"
    assert paper["timeframe"] == "1h"

    for filename in (
        "start-live-paused.ps1",
        "start-dryrun.ps1",
        "backtest.ps1",
        "lookahead-analysis.ps1",
        "recursive-analysis.ps1",
        "download-data.ps1",
    ):
        source = (SCRIPTS / filename).read_text(encoding="utf-8")
        assert "config-paper-runtime.json" not in source
        assert "$paperRuntimeOverlayPath" not in source


def test_startbot_routes_ui_auth_through_hardened_powershell_helper() -> None:
    start = (REPO_ROOT / "STARTBOT.bat").read_text(encoding="utf-8")
    password = (REPO_ROOT / "PASSWORT_AENDERN.bat").read_text(encoding="utf-8")
    helper = (SCRIPTS / "manage-testbot-ui-auth.ps1").read_text(encoding="utf-8")
    common = (SCRIPTS / "_common.ps1").read_text(encoding="utf-8")

    assert "manage-testbot-ui-auth.ps1" in start
    assert "-Mode Start" in start
    assert "PaperOnly-250-USDT!" not in start
    assert "set /p" not in password.lower()
    assert "-Mode ChangePassword" in password
    assert 'Read-Host "Neues Passwort (mindestens 14 Zeichen)" -AsSecureString' in helper
    assert "SetAccessRuleProtection($true, $false)" in helper
    assert "System.Security.Cryptography.DataProtectionScope]::CurrentUser" in helper
    assert "Add-Type -AssemblyName System.Security" in helper
    assert "Assert-SecureLocalAuthFile -Path $AuthFilePath" in helper
    assert 'FileAttributes]::Hidden' in helper
    assert ".testbot-ui-auth.json" in helper
    assert "New-CryptoToken -ByteCount 48" in helper
    assert "New-CryptoToken -ByteCount 32" in helper
    assert "$script:TestbotApiOverrideNames" in common
    assert "Enter-TestbotChildEnvironment" in common


def test_paper_ui_has_no_versioned_active_credentials() -> None:
    overlay_path = REPO_ROOT / "runtime" / "user_data" / "config-paper-public.json"
    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    assert "api_server" not in overlay
    assert overlay["exchange"]["ccxt_config"]["apiKey"] is None
    assert overlay["exchange"]["ccxt_async_config"]["apiKey"] is None

    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "runtime/user_data/.testbot-ui-auth.json" in ignored
    assert "runtime/user_data/.testbot-ui-auth.json.tmp.*" in ignored
    assert "runtime/user_data/.testbot-ui-auth.json.bak.*" in ignored


def test_api_query_secret_filter_redacts_only_secret_values() -> None:
    import logging

    from runtime.paper_locked_freqtrade import UvicornQuerySecretFilter

    record = logging.LogRecord(
        "uvicorn.error",
        logging.INFO,
        __file__,
        1,
        '127.0.0.1 - "WebSocket /api/v1/message/ws?token=%s&mode=paper" [accepted]',
        ("sensitive-token",),
        None,
    )
    assert UvicornQuerySecretFilter().filter(record) is True
    rendered = record.getMessage()
    assert "sensitive-token" not in rendered
    assert "token=[REDACTED]&mode=paper" in rendered
    assert "[accepted]" in rendered


def test_paper_wrapper_requires_child_owned_lock(tmp_path: Path) -> None:
    from runtime import paper_locked_freqtrade

    with pytest.raises(RuntimeError, match="exactly one --child-lock-file"):
        paper_locked_freqtrade.main(["--", "trade"])
    with pytest.raises(RuntimeError, match="must be absolute"):
        paper_locked_freqtrade.main(
            ["--child-lock-file", "relative.lock", "--", "trade"]
        )


@pytest.mark.skipif(os.name != "nt", reason="launcher uses Windows FileShare.None")
def test_python_child_lock_blocks_powershell_supervisor_lock(tmp_path: Path) -> None:
    """Prove the Python-held Win32 lock interoperates with WinPS File.Open."""

    lock_path = (tmp_path / "testbot-child.lock").resolve()
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "from pathlib import Path; "
                "from runtime.paper_locked_freqtrade import exclusive_child_lock; "
                f"p=Path({str(lock_path)!r}); "
                "ctx=exclusive_child_lock(p); ctx.__enter__(); "
                "print('LOCKED', flush=True); "
                "input(); ctx.__exit__(None, None, None)"
            ),
        ],
        cwd=REPO_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "LOCKED"
        probe = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-Command",
                (
                    "$ErrorActionPreference='Stop'; try { "
                    "$s=[IO.File]::Open($env:TEST_CHILD_LOCK,"
                    "[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,"
                    "[IO.FileShare]::None); $s.Dispose(); exit 9 "
                    "} catch [IO.IOException] { exit 0 }"
                ),
            ],
            cwd=REPO_ROOT,
            env={**os.environ, "TEST_CHILD_LOCK": str(lock_path)},
            capture_output=True,
            text=True,
            check=False,
        )
        assert probe.returncode == 0, probe.stderr
    finally:
        if holder.stdin is not None:
            holder.stdin.write("\n")
            holder.stdin.flush()
        _, stderr = holder.communicate(timeout=10)
        assert holder.returncode == 0, stderr

    released_probe = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "$ErrorActionPreference='Stop'; "
                "$s=[IO.File]::Open($env:TEST_CHILD_LOCK,"
                "[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,"
                "[IO.FileShare]::None); $s.Dispose()"
            ),
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "TEST_CHILD_LOCK": str(lock_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert released_probe.returncode == 0, released_probe.stderr


def test_local_auth_file_is_random_and_acl_protected(tmp_path: Path) -> None:
    auth_path = tmp_path / ".testbot-ui-auth.json"
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPTS / "manage-testbot-ui-auth.ps1"),
            "-Mode",
            "InitializeOnly",
            "-AuthFilePath",
            str(auth_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    assert auth["schema_version"] == 2
    assert auth["username"] == "testbot"
    assert "password" not in auth
    assert len(auth["password_dpapi"]) >= 40
    assert "jwt_secret_key" not in auth
    assert "ws_token" not in auth
    assert "PaperOnly-250-USDT!" not in auth_path.read_text(encoding="utf-8")

    second = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPTS / "manage-testbot-ui-auth.ps1"),
            "-Mode",
            "InitializeOnly",
            "-AuthFilePath",
            str(auth_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode == 0, second.stderr
    assert json.loads(auth_path.read_text(encoding="utf-8"))["password_dpapi"] == auth[
        "password_dpapi"
    ]


def test_local_auth_rejects_inherited_preseed_before_reading(tmp_path: Path) -> None:
    auth_path = tmp_path / ".testbot-ui-auth.json"
    original = '{"schema_version": 1, "username": "testbot", "password": "attacker-preseeded"}'
    auth_path.write_text(original, encoding="utf-8")

    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPTS / "manage-testbot-ui-auth.ps1"),
            "-Mode",
            "InitializeOnly",
            "-AuthFilePath",
            str(auth_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "beschaedigt oder unsicher" in (completed.stdout + completed.stderr)
    assert auth_path.read_text(encoding="utf-8") == original


def test_acl_protected_schema1_auth_is_atomically_upgraded_to_dpapi(
    tmp_path: Path,
) -> None:
    auth_path = tmp_path / ".testbot-ui-auth.json"
    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPTS / "manage-testbot-ui-auth.ps1"),
        "-Mode",
        "InitializeOnly",
        "-AuthFilePath",
        str(auth_path),
    ]
    first = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr

    old_password = "valid-old-password"
    legacy_json = json.dumps(
        {
            "schema_version": 1,
            "username": "testbot",
            "password": old_password,
            "created_at_utc": "2026-01-01T00:00:00Z",
        }
    )
    rewrite_environment = os.environ.copy()
    rewrite_environment["TEST_AUTH_PATH"] = str(auth_path)
    rewrite_environment["TEST_AUTH_JSON"] = legacy_json
    rewrite = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-Command",
            (
                "$path = $env:TEST_AUTH_PATH; "
                "$attributes = [IO.File]::GetAttributes($path); "
                "[IO.File]::SetAttributes($path, "
                "$attributes -band (-bnot [IO.FileAttributes]::Hidden)); "
                "[IO.File]::WriteAllText($path, $env:TEST_AUTH_JSON, "
                "[Text.UTF8Encoding]::new($false)); "
                "[IO.File]::SetAttributes($path, "
                "[IO.File]::GetAttributes($path) -bor [IO.FileAttributes]::Hidden)"
            ),
        ],
        cwd=REPO_ROOT,
        env=rewrite_environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rewrite.returncode == 0, rewrite.stderr
    second = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode == 0, second.stderr
    persisted_text = auth_path.read_text(encoding="utf-8")
    persisted = json.loads(persisted_text)
    assert persisted["schema_version"] == 2
    assert "password" not in persisted
    assert old_password not in persisted_text
    assert not list(tmp_path.glob(".testbot-ui-auth.json.tmp.*"))
    assert not list(tmp_path.glob(".testbot-ui-auth.json.bak.*"))


def test_short_legacy_plaintext_password_is_replaced_without_blocking_upgrade(
    tmp_path: Path,
) -> None:
    sandbox = tmp_path / "sandbox"
    scripts = sandbox / "runtime" / "scripts"
    user_data = sandbox / "runtime" / "user_data"
    scripts.mkdir(parents=True)
    user_data.mkdir(parents=True)
    helper = scripts / "manage-testbot-ui-auth.ps1"
    helper.write_bytes((SCRIPTS / "manage-testbot-ui-auth.ps1").read_bytes())
    legacy = user_data / ".testbot-ui-password"
    legacy.write_text("kurz", encoding="utf-8")

    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(helper),
            "-Mode",
            "InitializeOnly",
        ],
        cwd=sandbox,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert not legacy.exists()
    persisted = json.loads(
        (user_data / ".testbot-ui-auth.json").read_text(encoding="utf-8")
    )
    assert persisted["schema_version"] == 2
    assert "password" not in persisted
    assert len(persisted["password_dpapi"]) >= 40


def test_final_child_environment_retains_ui_auth_and_drops_unrelated_secret() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "FREQTRADE__API_SERVER__ENABLED": "true",
            "FREQTRADE__API_SERVER__USERNAME": "testbot",
            "FREQTRADE__API_SERVER__PASSWORD": "custom-password-works",
            "FREQTRADE__API_SERVER__JWT_SECRET_KEY": "j" * 64,
            "FREQTRADE__API_SERVER__WS_TOKEN": "w" * 43,
            "UNRELATED_CLOUD_SECRET_FOR_TEST": "must-not-reach-child",
            "TEST_COMMON_SOURCE": str(SCRIPTS / "_common.ps1"),
        }
    )
    script = r"""
. $env:TEST_COMMON_SOURCE
$saved = Enter-TestbotChildEnvironment -KillSwitchPath ".\runtime\user_data\DRYRUN_STOP_ENTRIES"
try {
    if ($env:FREQTRADE__API_SERVER__PASSWORD -ne "custom-password-works") {
        throw "custom UI password was removed"
    }
    if ($env:FREQTRADE__API_SERVER__JWT_SECRET_KEY.Length -ne 64) {
        throw "ephemeral JWT key was removed"
    }
    if ($env:FREQTRADE__API_SERVER__WS_TOKEN.Length -ne 43) {
        throw "ephemeral WebSocket key was removed"
    }
    if ($null -ne $env:UNRELATED_CLOUD_SECRET_FOR_TEST) {
        throw "unrelated secret reached child environment"
    }
    if ($env:FREQTRADE__DRY_RUN -ne "true") {
        throw "dry-run override is missing"
    }
} finally {
    Exit-TestbotChildEnvironment -SavedEnvironment $saved
}
if ($env:UNRELATED_CLOUD_SECRET_FOR_TEST -ne "must-not-reach-child") {
    throw "parent environment was not restored"
}
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


def test_interrupted_session_repair_is_dynamic_and_idempotent(tmp_path: Path) -> None:
    """Execute the real recovery function around a fake read-only exporter."""
    sessions = tmp_path / "sessions"
    session_id = "20260812T120000Z-pid-99999"
    session = sessions / session_id
    session.mkdir(parents=True)
    manifest = session / "session-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "session_id": session_id,
                "started_at_utc": "2026-08-12T12:00:00+00:00",
                "ended_at_utc": None,
                "status": "running",
                "freqtrade_exit_code": None,
                "report_status": "pending",
                "database": {"path": str(tmp_path / "old-session.sqlite")},
            }
        ),
        encoding="utf-8",
    )
    exporter = tmp_path / "fake-export.ps1"
    exporter.write_text(
        "param([string]$SessionStartUtc,[string]$SessionEndUtc,"
        "[string]$OutputDirectory,[string]$SessionId,[string]$DatabasePath)\n"
        "$value = @{ start=$SessionStartUtc; finish=$SessionEndUtc; "
        "id=$SessionId; database=$DatabasePath } "
        "| ConvertTo-Json\n"
        "[IO.File]::WriteAllText((Join-Path $OutputDirectory 'export-call.json'),$value)\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "TEST_LAUNCHER_SOURCE": str(SCRIPTS / "start-testbot-24x7.ps1"),
            "TEST_SESSIONS": str(sessions),
            "TEST_EXPORTER": str(exporter),
            "TEST_LOG": str(tmp_path / "recovery.log"),
        }
    )
    script = r"""
$ErrorActionPreference = "Stop"
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $env:TEST_LAUNCHER_SOURCE, [ref]$null, [ref]$null
)
$names = @(
    "Write-JsonAtomic",
    "Write-SupervisorLog",
    "Repair-InterruptedSessionManifests"
)
foreach ($name in $names) {
    $functionAst = $ast.Find({
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
            $node.Name -eq $name
    }, $true)
    Invoke-Expression $functionAst.Extent.Text
}
$utf8NoBom = [Text.UTF8Encoding]::new($false)
$script:SupervisorLogPath = $env:TEST_LOG
Repair-InterruptedSessionManifests `
    -SessionsDirectory $env:TEST_SESSIONS -ReportExporter $env:TEST_EXPORTER
Repair-InterruptedSessionManifests `
    -SessionsDirectory $env:TEST_SESSIONS -ReportExporter $env:TEST_EXPORTER
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
    repaired = json.loads(manifest.read_text(encoding="utf-8"))
    assert repaired["status"] == "interrupted"
    assert repaired["ended_at_utc"] is not None
    assert repaired["report_status"] == "created_after_interruption"
    assert repaired["interruption_detected_at_utc"] is not None
    assert (session / "export-call.json").is_file()
    export_call = json.loads((session / "export-call.json").read_text(encoding="utf-8"))
    assert export_call["database"] == str(tmp_path / "old-session.sqlite")
    assert (tmp_path / "recovery.log").read_text(encoding="utf-8").count(
        "Unterbrochene vorherige Sitzung abgeschlossen"
    ) == 1


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


def test_session_report_uses_database_recorded_in_manifest(tmp_path: Path) -> None:
    session_id = "old-strategy-session"
    database = (
        REPO_ROOT
        / "runtime"
        / "user_data"
        / "nonexistent-old-strategy-session.sqlite"
    ).resolve()
    (tmp_path / "session-manifest.json").write_text(
        json.dumps({"database": {"path": str(database)}}),
        encoding="utf-8",
    )
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
    report = json.loads(
        (tmp_path / f"dryrun-report-{session_id}.json").read_text(encoding="utf-8")
    )
    assert Path(report["source"]["database"]) == database
