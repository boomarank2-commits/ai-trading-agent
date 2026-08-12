[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$StrategyPath,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z_][A-Za-z0-9_]*$')]
    [string]$StrategyName
)

. (Join-Path $PSScriptRoot "_common.ps1")

$python = Join-Path $script:VenvPath "Scripts\python.exe"
$resolvedStrategy = (Resolve-Path -LiteralPath $StrategyPath).Path

Push-Location -LiteralPath $script:RepoRoot
try {
    & $python -m runtime.generate_deployment_manifest `
        --repository $script:RepoRoot `
        --strategy $resolvedStrategy `
        --strategy-name $StrategyName
    if ($LASTEXITCODE -ne 0) {
        throw "Deployment-manifest generation failed with code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
