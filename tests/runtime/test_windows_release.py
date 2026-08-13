from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "runtime" / "scripts"


def test_windows_setup_pins_and_verifies_runtime_and_ui_versions() -> None:
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runtime_dependencies = project["project"]["optional-dependencies"]["runtime"]
    setup = (SCRIPTS / "setup-venv.ps1").read_text(encoding="utf-8")

    assert "freqtrade==2026.7" in runtime_dependencies
    assert '$expectedFreqtradeVersion = "2026.7"' in setup
    assert '$expectedFreqUiVersion = "3.1.1"' in setup
    assert "sync --frozen --all-extras --python 3.12" in setup
    assert "sync --check --frozen --all-extras" in setup
    assert "version('freqtrade')" in setup
    assert "install-ui --ui-version $expectedFreqUiVersion" in setup
    assert 'Join-Path $freqUiDirectory ".uiversion"' in setup
    assert "$installedFreqUiVersion -ne $expectedFreqUiVersion" in setup
    assert "install-ui\n" not in setup


def test_session_manifest_records_exact_release_identity() -> None:
    launcher = (SCRIPTS / "start-testbot-24x7.ps1").read_text(encoding="utf-8")

    assert "schema_version = 2" in launcher
    assert "freqtrade_version = $freqtradeVersion" in launcher
    assert "frequi_version = $freqUiVersion" in launcher
    assert "git_commit = $gitCommit" in launcher
    assert "version('freqtrade')" in launcher
    assert ".uiversion" in launcher
    assert "rev-parse --verify HEAD" in launcher


def test_windows_ci_is_locked_validation_only() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "windows-ci.yml").read_text(
        encoding="utf-8"
    )

    assert "runs-on: windows-latest" in workflow
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflow
    assert "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97" in workflow
    assert "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9" in workflow
    assert "persist-credentials: false" in workflow
    assert 'python-version: "3.12"' in workflow
    assert 'version: "0.11.28"' in workflow
    assert "uv sync --frozen --all-extras --python 3.12" in workflow
    assert ".\\.venv\\Scripts\\python.exe -m pytest" in workflow
    assert ".\\.venv\\Scripts\\ruff.exe check ." in workflow
    assert "Language.Parser]::ParseFile" in workflow

    lowered = workflow.lower()
    assert "freqtrade trade" not in lowered
    assert "startbot.bat" not in lowered
    assert "start-testbot" not in lowered
    assert "start-live" not in lowered
