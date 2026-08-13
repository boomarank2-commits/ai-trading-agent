[CmdletBinding()]
param(
    [ValidateSet("Start", "ChangePassword", "InitializeOnly")]
    [string]$Mode = "Start",

    # Used only by automated contract tests. Normal launchers deliberately use
    # the fixed per-user LocalAppData path and never accept a path from batch.
    [string]$AuthFilePath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$runtimeRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $runtimeRoot ".."))
$userDataPath = Join-Path $runtimeRoot "user_data"
$launcherPath = Join-Path $PSScriptRoot "start-testbot-24x7.ps1"
$loginHelpPath = Join-Path $repoRoot "LOGIN_HILFE.html"
$repoLegacyCredentialPaths = @(
    (Join-Path $userDataPath ".testbot-ui-auth.json"),
    (Join-Path $userDataPath ".testbot-ui-password")
)
$localApplicationData = [Environment]::GetFolderPath(
    [Environment+SpecialFolder]::LocalApplicationData
)
if ([string]::IsNullOrWhiteSpace($localApplicationData)) {
    throw "Der lokale Windows-Anwendungsdatenordner konnte nicht ermittelt werden."
}
$defaultAuthDirectoryPath = [System.IO.Path]::GetFullPath(
    (Join-Path $localApplicationData "DaviddTech\AiTradingAgent\auth")
)
$defaultAuthFilePath = Join-Path $defaultAuthDirectoryPath "frequi-v2.json"
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$script:DpapiEntropy = [Text.Encoding]::UTF8.GetBytes("DaviddTech.ai-trading-agent.FreqUI.v2")

if ([string]::IsNullOrWhiteSpace($AuthFilePath)) {
    $AuthFilePath = $defaultAuthFilePath
}
$AuthFilePath = [System.IO.Path]::GetFullPath($AuthFilePath)
$isDefaultAuthPath = [string]::Equals(
    $AuthFilePath,
    $defaultAuthFilePath,
    [StringComparison]::OrdinalIgnoreCase
)

function Initialize-DpapiTypes {
    # Windows PowerShell 5.1 does not load System.Security eagerly, although
    # DPAPI's ProtectedData class is present in the full .NET Framework.
    try {
        Add-Type -AssemblyName System.Security -ErrorAction Stop
        [void][System.Security.Cryptography.ProtectedData]
        [void][System.Security.Cryptography.DataProtectionScope]
    }
    catch {
        throw "Windows-DPAPI konnte nicht geladen werden: $($_.Exception.Message)"
    }
}

Initialize-DpapiTypes

function New-CryptoToken {
    param([ValidateRange(16, 128)][int]$ByteCount)

    $bytes = New-Object byte[] $ByteCount
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
    }
    finally {
        $random.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function Assert-ValidUiPassword {
    param([Parameter(Mandatory = $true)][string]$Password)

    if ($Password.Length -lt 14) {
        throw "Das FreqUI-Passwort muss mindestens 14 Zeichen lang sein."
    }
    if ($Password.Length -gt 128) {
        throw "Das FreqUI-Passwort darf hoechstens 128 Zeichen lang sein."
    }
    if ($Password.ToCharArray() | Where-Object { [char]::IsControl($_) }) {
        throw "Das FreqUI-Passwort darf keine Steuerzeichen enthalten."
    }
}

function ConvertFrom-LocalSecureString {
    param([Parameter(Mandatory = $true)][Security.SecureString]$SecureValue)

    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Test-ConstantTimeEqual {
    param(
        [Parameter(Mandatory = $true)][string]$Left,
        [Parameter(Mandatory = $true)][string]$Right
    )

    # Compatible with Windows PowerShell 5.1 / .NET Framework, where
    # CryptographicOperations.FixedTimeEquals is not consistently available.
    $leftBytes = [Text.Encoding]::UTF8.GetBytes($Left)
    $rightBytes = [Text.Encoding]::UTF8.GetBytes($Right)
    $difference = $leftBytes.Length -bxor $rightBytes.Length
    $maximum = [Math]::Max($leftBytes.Length, $rightBytes.Length)
    for ($index = 0; $index -lt $maximum; $index++) {
        $leftByte = if ($index -lt $leftBytes.Length) { $leftBytes[$index] } else { 0 }
        $rightByte = if ($index -lt $rightBytes.Length) { $rightBytes[$index] } else { 0 }
        $difference = $difference -bor ($leftByte -bxor $rightByte)
    }
    return $difference -eq 0
}

function Assert-WindowsAuthStorageSupported {
    if ($env:OS -ne "Windows_NT") {
        throw "Lokale Zugangsdaten werden nur auf Windows mit DPAPI und Benutzer-ACL unterstuetzt."
    }
}

function Test-IsTrustedAuthOwner {
    param(
        [Parameter(Mandatory = $true)][Security.Principal.WindowsIdentity]$Identity,
        [Parameter(Mandatory = $true)][string]$OwnerSid
    )

    if ($OwnerSid -eq $Identity.User.Value) {
        return $true
    }

    # GitHub's elevated Windows runner can create its temporary directories
    # with BUILTIN\Administrators as owner. Accept that owner only when this
    # process is itself running with the active Administrator role. A normal
    # UAC-filtered desktop process therefore still requires the user's SID.
    $administratorsSid = "S-1-5-32-544"
    if ($OwnerSid -ne $administratorsSid) {
        return $false
    }
    $principal = New-Object Security.Principal.WindowsPrincipal($Identity)
    return $principal.IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator
    )
}

function Assert-SecureLocalAuthDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    Assert-WindowsAuthStorageSupported
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) {
        throw "Der lokale FreqUI-Zugangsdatenpfad ist kein Verzeichnis."
    }
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Das lokale FreqUI-Zugangsdatenverzeichnis darf kein Link oder Reparse-Point sein."
    }

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        $currentSid = $identity.User.Value
        $acl = [System.IO.Directory]::GetAccessControl($Path)
        $ownerSid = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        if (-not (Test-IsTrustedAuthOwner -Identity $identity -OwnerSid $ownerSid)) {
            throw "Das lokale FreqUI-Zugangsdatenverzeichnis gehoert nicht dem aktuellen Windows-Benutzer."
        }
        if (-not $acl.AreAccessRulesProtected) {
            throw "Das lokale FreqUI-Zugangsdatenverzeichnis erbt unerwartete Zugriffsregeln."
        }

        $rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
        if ($rules.Count -ne 1) {
            throw "Das lokale FreqUI-Zugangsdatenverzeichnis hat unerwartete Zugriffsregeln."
        }
        $rule = $rules[0]
        $expectedInheritance = (
            [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
            [Security.AccessControl.InheritanceFlags]::ObjectInherit
        )
        if (
            $rule.IdentityReference.Value -ne $currentSid -or
            $rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            $rule.IsInherited -or
            [int]$rule.FileSystemRights -ne [int][Security.AccessControl.FileSystemRights]::FullControl -or
            $rule.InheritanceFlags -ne $expectedInheritance -or
            $rule.PropagationFlags -ne [Security.AccessControl.PropagationFlags]::None
        ) {
            throw "Das lokale FreqUI-Zugangsdatenverzeichnis ist nicht exklusiv auf den aktuellen Windows-Benutzer begrenzt."
        }
    }
    finally {
        $identity.Dispose()
    }
}

function Protect-LocalAuthDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    Assert-WindowsAuthStorageSupported
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) {
        throw "Der lokale FreqUI-Zugangsdatenpfad ist kein Verzeichnis."
    }
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Das lokale FreqUI-Zugangsdatenverzeichnis darf kein Link oder Reparse-Point sein."
    }

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        # Ownership is verified before changing the DACL. Never call SetOwner:
        # an owner may harden a DACL without the WRITE_OWNER privilege, which
        # is important in ordinary project folders that grant only Modify.
        $security = [System.IO.Directory]::GetAccessControl($Path)
        $ownerSid = $security.GetOwner([Security.Principal.SecurityIdentifier]).Value
        if (-not (Test-IsTrustedAuthOwner -Identity $identity -OwnerSid $ownerSid)) {
            throw "Das lokale FreqUI-Zugangsdatenverzeichnis gehoert nicht dem aktuellen Windows-Benutzer."
        }
        $security.SetAccessRuleProtection($true, $false)
        $explicitRules = @(
            $security.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier])
        )
        foreach ($existingRule in $explicitRules) {
            [void]$security.RemoveAccessRuleSpecific($existingRule)
        }
        $rule = New-Object Security.AccessControl.FileSystemAccessRule(
            $identity.User,
            [Security.AccessControl.FileSystemRights]::FullControl,
            (
                [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor
                [Security.AccessControl.InheritanceFlags]::ObjectInherit
            ),
            [Security.AccessControl.PropagationFlags]::None,
            [Security.AccessControl.AccessControlType]::Allow
        )
        [void]$security.AddAccessRule($rule)
        [System.IO.Directory]::SetAccessControl($Path, $security)
    }
    finally {
        $identity.Dispose()
    }
    Assert-SecureLocalAuthDirectory -Path $Path
}

function Initialize-SecureLocalAuthDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        $existing = Get-Item -LiteralPath $Path -Force
        if (-not $existing.PSIsContainer) {
            throw "Der lokale FreqUI-Zugangsdatenpfad ist kein Verzeichnis: $Path"
        }
    }
    else {
        [System.IO.Directory]::CreateDirectory($Path) | Out-Null
    }
    Protect-LocalAuthDirectory -Path $Path
}

function Protect-LocalAuthFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    Assert-WindowsAuthStorageSupported
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer) {
        throw "Der lokale FreqUI-Zugangsdatenpfad ist keine Datei."
    }
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Die lokale FreqUI-Zugangsdaten-Datei darf kein Link oder Reparse-Point sein."
    }
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        # Work on the existing descriptor and change only its DACL. Setting
        # the already-correct owner would unnecessarily require WRITE_OWNER.
        $security = [System.IO.File]::GetAccessControl($Path)
        $ownerSid = $security.GetOwner([Security.Principal.SecurityIdentifier]).Value
        if (-not (Test-IsTrustedAuthOwner -Identity $identity -OwnerSid $ownerSid)) {
            throw "Die lokale FreqUI-Zugangsdaten-Datei gehoert nicht dem aktuellen Windows-Benutzer."
        }
        $security.SetAccessRuleProtection($true, $false)
        $explicitRules = @(
            $security.GetAccessRules($true, $false, [Security.Principal.SecurityIdentifier])
        )
        foreach ($existingRule in $explicitRules) {
            [void]$security.RemoveAccessRuleSpecific($existingRule)
        }
        $rule = New-Object Security.AccessControl.FileSystemAccessRule(
            $identity.User,
            [Security.AccessControl.FileSystemRights]::FullControl,
            [Security.AccessControl.AccessControlType]::Allow
        )
        [void]$security.AddAccessRule($rule)
        [System.IO.File]::SetAccessControl($Path, $security)
        $attributes = [System.IO.File]::GetAttributes($Path)
        [System.IO.File]::SetAttributes($Path, $attributes -bor [System.IO.FileAttributes]::Hidden)
    }
    finally {
        $identity.Dispose()
    }
}

function Assert-SecureLocalAuthFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    Assert-WindowsAuthStorageSupported
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.PSIsContainer) {
        throw "Der lokale FreqUI-Zugangsdatenpfad ist keine Datei."
    }
    if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Die lokale FreqUI-Zugangsdaten-Datei darf kein Link oder Reparse-Point sein."
    }

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    try {
        $currentSid = $identity.User.Value
        # Use the .NET API directly. GitHub's minimal Windows runner can fail
        # to autoload Microsoft.PowerShell.Security for Get-Acl even though
        # the underlying FileSecurity API is available (as it is on WinPS 5.1).
        $acl = [System.IO.File]::GetAccessControl($Path)
        $ownerSid = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
        if (-not (Test-IsTrustedAuthOwner -Identity $identity -OwnerSid $ownerSid)) {
            throw "Die lokale FreqUI-Zugangsdaten-Datei gehoert nicht dem aktuellen Windows-Benutzer."
        }
        if (-not $acl.AreAccessRulesProtected) {
            throw "Die lokale FreqUI-Zugangsdaten-Datei erbt unerwartete Zugriffsregeln."
        }

        $rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))
        if ($rules.Count -ne 1) {
            throw "Die lokale FreqUI-Zugangsdaten-Datei hat unerwartete Zugriffsregeln."
        }
        $rule = $rules[0]
        if (
            $rule.IdentityReference.Value -ne $currentSid -or
            $rule.AccessControlType -ne [Security.AccessControl.AccessControlType]::Allow -or
            $rule.IsInherited -or
            [int]$rule.FileSystemRights -ne [int][Security.AccessControl.FileSystemRights]::FullControl
        ) {
            throw "Die lokale FreqUI-Zugangsdaten-Datei ist nicht exklusiv auf den aktuellen Windows-Benutzer begrenzt."
        }
    }
    finally {
        $identity.Dispose()
    }
}

function Protect-UiPassword {
    param([Parameter(Mandatory = $true)][string]$Password)

    if ($env:OS -ne "Windows_NT") {
        throw "Das lokale FreqUI-Passwort kann nur auf Windows mit DPAPI geschuetzt werden."
    }
    $plainBytes = [Text.Encoding]::UTF8.GetBytes($Password)
    $protectedBytes = $null
    try {
        $protectedBytes = [System.Security.Cryptography.ProtectedData]::Protect(
            $plainBytes,
            $script:DpapiEntropy,
            [System.Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        return [Convert]::ToBase64String($protectedBytes)
    }
    finally {
        [Array]::Clear($plainBytes, 0, $plainBytes.Length)
        if ($null -ne $protectedBytes) {
            [Array]::Clear($protectedBytes, 0, $protectedBytes.Length)
        }
    }
}

function Unprotect-UiPassword {
    param([Parameter(Mandatory = $true)][string]$ProtectedPassword)

    if ($env:OS -ne "Windows_NT") {
        throw "Das lokale FreqUI-Passwort kann nur unter dem zugehoerigen Windows-Benutzer gelesen werden."
    }
    $protectedBytes = [Convert]::FromBase64String($ProtectedPassword)
    $plainBytes = $null
    try {
        $plainBytes = [System.Security.Cryptography.ProtectedData]::Unprotect(
            $protectedBytes,
            $script:DpapiEntropy,
            [System.Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        return [Text.Encoding]::UTF8.GetString($plainBytes)
    }
    finally {
        [Array]::Clear($protectedBytes, 0, $protectedBytes.Length)
        if ($null -ne $plainBytes) {
            [Array]::Clear($plainBytes, 0, $plainBytes.Length)
        }
    }
}

function Write-LocalAuthAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Value
    )

    $directory = [System.IO.Path]::GetDirectoryName($Path)
    Initialize-SecureLocalAuthDirectory -Path $directory
    if (Test-Path -LiteralPath $Path) {
        if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
            throw "Der lokale FreqUI-Zugangsdatenpfad ist keine Datei: $Path"
        }
        # An existing destination is always verified before it can be read or
        # replaced. It is never silently repaired from an untrusted state.
        Assert-SecureLocalAuthFile -Path $Path
    }
    $filename = [System.IO.Path]::GetFileName($Path)
    $suffix = "$PID.$([Guid]::NewGuid().ToString('N'))"
    $temporary = Join-Path $directory "$filename.tmp.$suffix"
    $backup = Join-Path $directory "$filename.bak.$suffix"
    $json = ($Value | ConvertTo-Json -Depth 5) + [Environment]::NewLine
    try {
        [System.IO.File]::WriteAllText($temporary, $json, $utf8NoBom)
        Protect-LocalAuthFile -Path $temporary
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            Assert-SecureLocalAuthFile -Path $Path
            [System.IO.File]::Replace($temporary, $Path, $backup)
        }
        else {
            [System.IO.File]::Move($temporary, $Path)
        }
        Protect-LocalAuthFile -Path $Path
        Assert-SecureLocalAuthFile -Path $Path
    }
    finally {
        foreach ($candidate in @($temporary, $backup)) {
            if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                Remove-Item -LiteralPath $candidate -Force
            }
        }
    }
}

function Assert-ValidAuthRecord {
    param([Parameter(Mandatory = $true)][object]$Auth)

    if ([int]$Auth.schema_version -ne 2) {
        throw "Die lokale FreqUI-Zugangsdaten-Datei hat eine unbekannte Version."
    }
    if ([string]$Auth.username -ne "testbot") {
        throw "Der lokale FreqUI-Benutzer muss testbot sein."
    }
    $propertyNames = @($Auth.PSObject.Properties.Name)
    if ($propertyNames -contains "password") {
        throw "Die lokale FreqUI-Zugangsdaten-Datei darf kein Klartext-Passwort enthalten."
    }
    if ([string]::IsNullOrWhiteSpace([string]$Auth.password_dpapi)) {
        throw "Die lokale FreqUI-Zugangsdaten-Datei enthaelt kein DPAPI-geschuetztes Passwort."
    }
}

function New-AuthRecord {
    param(
        [Parameter(Mandatory = $true)][string]$Password,
        [string]$CreatedAtUtc = ""
    )

    Assert-ValidUiPassword -Password $Password
    $now = [DateTimeOffset]::UtcNow.ToString("o")
    if ([string]::IsNullOrWhiteSpace($CreatedAtUtc)) {
        $CreatedAtUtc = $now
    }
    return [ordered]@{
        schema_version = 2
        username = "testbot"
        password_dpapi = Protect-UiPassword -Password $Password
        created_at_utc = $CreatedAtUtc
        password_changed_at_utc = $now
    }
}

function Read-VerifiedV2Auth {
    param([Parameter(Mandatory = $true)][string]$Path)

    # This check must happen before the first byte is read. An attacker-created
    # or inherited/preseeded file is rejected rather than silently repaired.
    Assert-SecureLocalAuthFile -Path $Path
    $record = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-ValidAuthRecord -Auth $record
    $password = Unprotect-UiPassword -ProtectedPassword ([string]$record.password_dpapi)
    Assert-ValidUiPassword -Password $password
    return [pscustomobject]@{
        Record = $record
        Auth = [pscustomobject]@{
            username = [string]$record.username
            password = $password
        }
        CreatedAtUtc = [string]$record.created_at_utc
    }
}

function New-AuthResult {
    param(
        [Parameter(Mandatory = $true)][object]$Loaded,
        [Parameter(Mandatory = $true)][bool]$Created,
        [Parameter(Mandatory = $true)][bool]$Migrated,
        [Parameter(Mandatory = $true)][bool]$RevealPassword,
        [Parameter(Mandatory = $true)][string]$MigrationKind
    )

    return [pscustomobject]@{
        Auth = $Loaded.Auth
        CreatedAtUtc = $Loaded.CreatedAtUtc
        Created = $Created
        Migrated = $Migrated
        RevealPassword = $RevealPassword
        MigrationKind = $MigrationKind
    }
}

function Test-RepoLegacyCredentialsExist {
    if (-not $isDefaultAuthPath) {
        return $false
    }
    foreach ($legacyPath in $repoLegacyCredentialPaths) {
        if (Test-Path -LiteralPath $legacyPath) {
            return $true
        }
    }
    return $false
}

function Remove-RepoLegacyCredentialsBestEffort {
    if (-not $isDefaultAuthPath) {
        return
    }
    # Neither repository-local legacy file is ever read or imported. Cleanup
    # starts only after the new LocalAppData DPAPI-v2 record was verified and
    # must never prevent a safe bot start if the old file is locked.
    foreach ($legacyPath in $repoLegacyCredentialPaths) {
        if (-not (Test-Path -LiteralPath $legacyPath)) {
            continue
        }
        try {
            if (Test-Path -LiteralPath $legacyPath -PathType Leaf) {
                Remove-Item -LiteralPath $legacyPath -Force -ErrorAction Stop
                Write-Host "Inaktive alte Zugangsdaten-Datei wurde entfernt: $legacyPath"
            }
            else {
                Write-Warning "Inaktiver alter Zugangsdatenpfad ist keine Datei und wurde nicht entfernt: $legacyPath"
            }
        }
        catch {
            Write-Warning (
                "Inaktive alte Zugangsdaten-Datei konnte nicht entfernt werden. " +
                "Sie wird NICHT verwendet und kann spaeter manuell geloescht werden: " +
                "$legacyPath ($($_.Exception.Message))"
            )
        }
    }
}

function Get-OrCreateLocalAuth {
    $authDirectory = [System.IO.Path]::GetDirectoryName($AuthFilePath)
    Initialize-SecureLocalAuthDirectory -Path $authDirectory

    if (Test-Path -LiteralPath $AuthFilePath -PathType Leaf) {
        try {
            # Validate owner and DACL before parsing even a legacy schema.
            Assert-SecureLocalAuthFile -Path $AuthFilePath
            $persisted = Get-Content -LiteralPath $AuthFilePath -Raw -Encoding UTF8 | ConvertFrom-Json
            $schemaVersion = [int]$persisted.schema_version
            if ($schemaVersion -eq 2) {
                $loaded = Read-VerifiedV2Auth -Path $AuthFilePath
                $repoLegacyFound = Test-RepoLegacyCredentialsExist
                Remove-RepoLegacyCredentialsBestEffort
                $kind = if ($repoLegacyFound) { "RepoLegacyDiscarded" } else { "Existing" }
                return New-AuthResult -Loaded $loaded -Created $false -Migrated $repoLegacyFound -RevealPassword $false -MigrationKind $kind
            }
            if ($schemaVersion -ne 1) {
                throw "Die lokale FreqUI-Zugangsdaten-Datei hat eine unbekannte Version."
            }
            if ([string]$persisted.username -ne "testbot") {
                throw "Der lokale FreqUI-Benutzer muss testbot sein."
            }

            $migrationKind = "Schema1Encrypted"
            $revealPassword = $false
            $password = [string]$persisted.password
            try {
                Assert-ValidUiPassword -Password $password
            }
            catch {
                # Early local builds allowed shorter plaintext passwords. They
                # are replaced, not allowed to strand the upgrade or persist.
                $password = New-CryptoToken -ByteCount 18
                $migrationKind = "Schema1Reset"
                $revealPassword = $true
            }
            $createdAtUtc = [string]$persisted.created_at_utc
            $record = New-AuthRecord -Password $password -CreatedAtUtc $createdAtUtc
            Write-LocalAuthAtomic -Path $AuthFilePath -Value $record
            $loaded = Read-VerifiedV2Auth -Path $AuthFilePath
            Remove-RepoLegacyCredentialsBestEffort
            return New-AuthResult -Loaded $loaded -Created $false -Migrated $true -RevealPassword $revealPassword -MigrationKind $migrationKind
        }
        catch {
            throw "Lokale FreqUI-Zugangsdaten sind beschaedigt oder unsicher: $($_.Exception.Message)"
        }
    }

    $repoLegacyFound = Test-RepoLegacyCredentialsExist
    # Never trust or import either repository-local legacy file. Generate and
    # verify a new LocalAppData credential before best-effort cleanup.
    $password = New-CryptoToken -ByteCount 18
    $record = New-AuthRecord -Password $password
    Write-LocalAuthAtomic -Path $AuthFilePath -Value $record
    $loaded = Read-VerifiedV2Auth -Path $AuthFilePath
    Remove-RepoLegacyCredentialsBestEffort
    $kind = if ($repoLegacyFound) { "RepoLegacyReset" } else { "New" }
    return New-AuthResult -Loaded $loaded -Created (-not $repoLegacyFound) -Migrated $repoLegacyFound -RevealPassword $true -MigrationKind $kind
}

$result = Get-OrCreateLocalAuth

if ($Mode -eq "InitializeOnly") {
    Assert-SecureLocalAuthFile -Path $AuthFilePath
    Write-Output "Lokale FreqUI-Zugangsdaten sind vorbereitet, DPAPI-verschluesselt und ACL-geschuetzt."
    exit 0
}

if ($Mode -eq "ChangePassword") {
    Write-Host ""
    Write-Host "Das Passwort wird bei der Eingabe nicht angezeigt."
    $firstSecure = Read-Host "Neues Passwort (mindestens 14 Zeichen)" -AsSecureString
    $secondSecure = Read-Host "Neues Passwort wiederholen" -AsSecureString
    $first = ConvertFrom-LocalSecureString -SecureValue $firstSecure
    $second = ConvertFrom-LocalSecureString -SecureValue $secondSecure
    try {
        Assert-ValidUiPassword -Password $first
        if (-not (Test-ConstantTimeEqual -Left $first -Right $second)) {
            throw "Die beiden Passwoerter stimmen nicht ueberein."
        }
        $record = New-AuthRecord -Password $first -CreatedAtUtc $result.CreatedAtUtc
        Write-LocalAuthAtomic -Path $AuthFilePath -Value $record
        [void](Read-VerifiedV2Auth -Path $AuthFilePath)
    }
    finally {
        $first = $null
        $second = $null
        $firstSecure.Dispose()
        $secondSecure.Dispose()
    }
    Write-Host ""
    Write-Host "Das neue lokale Passwort wurde sicher gespeichert."
    Write-Host "Es wird beim naechsten STARTBOT-Start aktiv."
    exit 0
}

if (-not (Test-Path -LiteralPath $launcherPath -PathType Leaf)) {
    throw "Testbot-Launcher fehlt: $launcherPath"
}

Write-Host "FreqUI-Adresse : http://127.0.0.1:8080"
Write-Host "FreqUI-Benutzer: testbot"
if ($result.RevealPassword) {
    Write-Host ""
    if ($result.MigrationKind -eq "RepoLegacyReset") {
        Write-Host "SICHERER WECHSEL - alte Repo-Zugangsdaten werden nicht mehr verwendet." -ForegroundColor Yellow
        Write-Host "Im geschuetzten Windows-Speicher wurde ein neues Passwort erzeugt:" -ForegroundColor Yellow
    }
    elseif ($result.MigrationKind -eq "Schema1Reset") {
        Write-Host "SICHERE MIGRATION - das alte zu kurze Passwort wurde ersetzt:" -ForegroundColor Yellow
    }
    else {
        Write-Host "ERSTE ANMELDUNG - automatisch erzeugtes lokales Passwort:" -ForegroundColor Yellow
    }
    Write-Host ([string]$result.Auth.password) -ForegroundColor Yellow
    Write-Host "Dieses Passwort ist DPAPI-geschuetzt an diesen Windows-Benutzer gebunden. Bitte jetzt notieren."
    if (Test-Path -LiteralPath $loginHelpPath -PathType Leaf) {
        Start-Process -FilePath $loginHelpPath
    }
}
elseif ($result.Migrated) {
    if ($result.MigrationKind -eq "RepoLegacyDiscarded") {
        Write-Host "Alte Repo-Zugangsdaten sind inaktiv; das geschuetzte LocalAppData-Passwort bleibt aktiv."
    }
    else {
        Write-Host "Das bisherige lokale Passwort wurde aus Klartext in den DPAPI-Speicher migriert."
    }
}
else {
    Write-Host "FreqUI-Passwort: eigenes lokales Passwort ist aktiv"
}
Write-Host ""

$overrideNames = @(
    "FREQTRADE__API_SERVER__ENABLED",
    "FREQTRADE__API_SERVER__USERNAME",
    "FREQTRADE__API_SERVER__PASSWORD",
    "FREQTRADE__API_SERVER__JWT_SECRET_KEY",
    "FREQTRADE__API_SERVER__WS_TOKEN"
)
$previous = @{}
foreach ($name in $overrideNames) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name, [EnvironmentVariableTarget]::Process)
}
try {
    $env:FREQTRADE__API_SERVER__ENABLED = "true"
    $env:FREQTRADE__API_SERVER__USERNAME = [string]$result.Auth.username
    $env:FREQTRADE__API_SERVER__PASSWORD = [string]$result.Auth.password
    # These authentication keys are deliberately generated anew for every
    # start. They are neither persisted nor written to a manifest or log.
    $env:FREQTRADE__API_SERVER__JWT_SECRET_KEY = New-CryptoToken -ByteCount 48
    $env:FREQTRADE__API_SERVER__WS_TOKEN = New-CryptoToken -ByteCount 32
    & $launcherPath
}
finally {
    foreach ($name in $overrideNames) {
        if ($null -eq $previous[$name]) {
            Remove-Item -LiteralPath "Env:$name" -ErrorAction SilentlyContinue
        }
        else {
            [Environment]::SetEnvironmentVariable(
                $name,
                [string]$previous[$name],
                [EnvironmentVariableTarget]::Process
            )
        }
    }
}
