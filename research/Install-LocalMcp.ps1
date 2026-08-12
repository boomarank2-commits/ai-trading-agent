[CmdletBinding()]
param(
    [string]$Database,
    [switch]$Install
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"

if ([string]::IsNullOrWhiteSpace($Database)) {
    $Database = Join-Path $repoRoot "research\registry\strategies.sqlite3"
}
$databasePath = [System.IO.Path]::GetFullPath($Database)

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Python environment not found at '$pythonPath'. Install the project environment first."
}
if (-not (Test-Path -LiteralPath $databasePath -PathType Leaf)) {
    throw "Registry not found at '$databasePath'. Initialize it before registering the MCP server; see research\MCP.md."
}

$codexCommand = Get-Command "codex.cmd" -ErrorAction Stop
$arguments = @(
    "mcp",
    "add",
    "local-trader",
    "--",
    $pythonPath,
    "-m",
    "local_trader.mcp_server",
    "--db",
    $databasePath
)

function Format-CommandArgument {
    param([Parameter(Mandatory = $true)][string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

$displayArguments = $arguments | ForEach-Object { Format-CommandArgument -Value $_ }
$displayCommand = "& " + (Format-CommandArgument -Value $codexCommand.Source) + " " + ($displayArguments -join " ")

Write-Host "Research-only MCP command:"
Write-Host $displayCommand

if (-not $Install) {
    Write-Host "Preview only. Re-run with -Install to update the Codex MCP configuration."
    exit 0
}

& $codexCommand.Source @arguments
if ($LASTEXITCODE -ne 0) {
    throw "codex mcp add failed with exit code $LASTEXITCODE"
}

Write-Host "Registered 'local-trader'. Restart or refresh Codex MCP discovery if needed."
