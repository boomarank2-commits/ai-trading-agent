Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:RuntimeRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$script:RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $script:RuntimeRoot ".."))
$script:UserDataPath = Join-Path $script:RuntimeRoot "user_data"
$script:ConfigPath = Join-Path $script:UserDataPath "config.json"
$script:PublicOverlayPath = Join-Path $script:UserDataPath "config-paper-public.json"
$script:AnalysisOverlayPath = Join-Path $script:UserDataPath "config-analysis.json"
$script:LiveOverlayPath = Join-Path $script:UserDataPath "config-live.example.json"
$script:VenvPath = Join-Path $script:RepoRoot ".venv"
$script:FreqtradeExe = Join-Path $script:VenvPath "Scripts\freqtrade.exe"
$script:StrategyName = "CompressionBreakout250"

function Assert-RuntimeLayout {
    if (-not (Test-Path -LiteralPath $script:ConfigPath -PathType Leaf)) {
        throw "Freqtrade config not found: $script:ConfigPath"
    }
    if (-not (Test-Path -LiteralPath $script:PublicOverlayPath -PathType Leaf)) {
        throw "Public-data overlay not found: $script:PublicOverlayPath"
    }
    if (-not (Test-Path -LiteralPath $script:AnalysisOverlayPath -PathType Leaf)) {
        throw "Analysis overlay not found: $script:AnalysisOverlayPath"
    }
    if (-not (Test-Path -LiteralPath $script:FreqtradeExe -PathType Leaf)) {
        throw "Freqtrade is not installed in the repository .venv. Run scripts/setup-venv.ps1 first."
    }
}

$script:TestbotApiOverrideNames = @(
    "FREQTRADE__API_SERVER__ENABLED",
    "FREQTRADE__API_SERVER__USERNAME",
    "FREQTRADE__API_SERVER__PASSWORD",
    "FREQTRADE__API_SERVER__JWT_SECRET_KEY",
    "FREQTRADE__API_SERVER__WS_TOKEN"
)

function Assert-NoFreqtradeOverrides {
    param([string[]]$Allowed = @())

    $unexpected = @(Get-ChildItem Env:FREQTRADE__* -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -notin $Allowed
    })
    if ($unexpected.Count -gt 0) {
        $names = ($unexpected.Name | Sort-Object) -join ", "
        throw "Refusing command because unapproved Freqtrade overrides are inherited: $names"
    }
}

function Assert-TestbotApiEnvironment {
    $values = @{}
    foreach ($name in $script:TestbotApiOverrideNames) {
        $values[$name] = [Environment]::GetEnvironmentVariable(
            $name,
            [EnvironmentVariableTarget]::Process
        )
        if ([string]::IsNullOrWhiteSpace([string]$values[$name])) {
            throw "Der gesicherte STARTBOT-Aufruf hat unvollstaendige lokale FreqUI-Zugangsdaten."
        }
    }
    if ([string]$values["FREQTRADE__API_SERVER__ENABLED"] -ne "true") {
        throw "FreqUI darf im Testbot nur explizit fuer den lokalen Dry-run aktiviert werden."
    }
    if ([string]$values["FREQTRADE__API_SERVER__USERNAME"] -ne "testbot") {
        throw "Der lokale FreqUI-Benutzer muss testbot sein."
    }
    $password = [string]$values["FREQTRADE__API_SERVER__PASSWORD"]
    if ($password.Length -lt 14 -or $password.Length -gt 128) {
        throw "Das lokale FreqUI-Passwort hat eine unzulaessige Laenge."
    }
    if ($password.ToCharArray() | Where-Object { [char]::IsControl($_) }) {
        throw "Das lokale FreqUI-Passwort enthaelt unzulaessige Steuerzeichen."
    }
    foreach ($name in @(
        "FREQTRADE__API_SERVER__JWT_SECRET_KEY",
        "FREQTRADE__API_SERVER__WS_TOKEN"
    )) {
        if ([string]$values[$name] -notmatch '^[A-Za-z0-9_-]{43,}$') {
            throw "Ein fluechtiger lokaler FreqUI-Schluessel ist ungueltig."
        }
    }
}

function Enter-TestbotChildEnvironment {
    param([Parameter(Mandatory = $true)][string]$KillSwitchPath)

    Assert-TestbotApiEnvironment
    $saved = @{}
    $allowlist = @(
        "ALLUSERSPROFILE", "APPDATA", "COMSPEC", "HOMEDRIVE", "HOMEPATH",
        "LOCALAPPDATA", "NUMBER_OF_PROCESSORS", "OS", "PATH", "PATHEXT",
        "PROCESSOR_ARCHITECTURE", "PROGRAMDATA", "PROGRAMFILES",
        "PROGRAMFILES(X86)", "SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "TMP",
        "USERDOMAIN", "USERNAME", "USERPROFILE", "WINDIR"
    ) + $script:TestbotApiOverrideNames
    Get-ChildItem Env: | ForEach-Object {
        $saved[$_.Name] = $_.Value
        if ($_.Name -notin $allowlist) {
            Remove-Item -ErrorAction SilentlyContinue -LiteralPath "Env:$($_.Name)"
        }
    }
    $env:FREQTRADE__DRY_RUN = "true"
    $env:FREQTRADE__INITIAL_STATE = "running"
    $env:AI_TRADING_KILL_SWITCH_FILE = [System.IO.Path]::GetFullPath($KillSwitchPath)
    return $saved
}

function Exit-TestbotChildEnvironment {
    param([Parameter(Mandatory = $true)][hashtable]$SavedEnvironment)

    Get-ChildItem Env: | ForEach-Object {
        Remove-Item -ErrorAction SilentlyContinue -LiteralPath "Env:$($_.Name)"
    }
    foreach ($name in $SavedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable(
            $name,
            [string]$SavedEnvironment[$name],
            [EnvironmentVariableTarget]::Process
        )
    }
}

function Invoke-FreqtradeCommand {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$CommandArgs
    )

    Assert-RuntimeLayout
    Push-Location -LiteralPath $script:RuntimeRoot
    try {
        & $script:FreqtradeExe @CommandArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Freqtrade exited with code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
