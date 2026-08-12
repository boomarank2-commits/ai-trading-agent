# Registry-v4-Workflow

Die Registry ist ein unveränderliches Forschungsledger und keine
Handelserlaubnis. Operative Befehle geben genau ein JSON-Objekt aus; ein Fehler
endet mit einem Exitcode ungleich null. `--help` gibt normalen Argparse-Text
aus. Die lokale Datenbank ist
`research/registry/strategies.sqlite3` und bleibt außerhalb von Git.

## 1. Kandidat bewusst importieren

Ein künftig extern isolierter Research-Zyklus darf Ergebnisse ausschließlich
zur menschlichen Übernahme bereitstellen; der lokale autonome Scheduler ist
hart deaktiviert. Nach einem manuellen Code- und Ergebnisreview darf die
geprüfte Python-Datei nach
`runtime/user_data/strategies/candidates/` kopiert und registriert werden:

```powershell
$db = Resolve-Path .\research\registry\strategies.sqlite3
$candidate = Resolve-Path .\runtime\user_data\strategies\candidates\MyStrategy.py

$candidateRegistration = & .\.venv\Scripts\python.exe -m local_trader --db $db register `
  --name MyStrategy `
  --source $candidate | ConvertFrom-Json
$candidateVersion = [int]$candidateRegistration.version.version
```

Danach ist der registrierte Datei-Hash unveränderlich. Jede Codeänderung ist
eine neue Version. Derselbe Hash darf pro Strategiename und Source-Root nur
einmal vorkommen. Nach einer bereits aktiven promoteten Version muss ein neuer
Kandidat mit `--parent-version` ausdrücklich von der gewünschten älteren
Kandidatenversion abstammen; ein Candidate darf keinen Promoted-Parent haben.
`verify`, `status` und `list` sind reine Leseprüfungen:

```powershell
& .\.venv\Scripts\python.exe -m local_trader --db $db verify `
  --strategy MyStrategy --version $candidateVersion
& .\.venv\Scripts\python.exe -m local_trader --db $db status `
  --strategy MyStrategy --version $candidateVersion
& .\.venv\Scripts\python.exe -m local_trader --db $db list
```

`list` zeigt nur die jeweils aktive Version. Nur die allererste Registrierung
wird automatisch aktiv; jede weitere Candidate- oder Promoted-Version lässt
den bisherigen Active-Zeiger unverändert. Deshalb immer die Versionsnummer aus
dem jeweiligen Register-JSON weiterreichen und bei mehr als einer Version
`status`, `evaluate`, `promote` und `verify` ausdrücklich mit `--version`
aufrufen.

## 2. Evidenz stufengerecht erfassen

Der erlaubte Weg ist:

```text
IDEA -> RESEARCH -> VALIDATED -> HOLDOUT_PASSED -> SHADOW
     -> PAPER -> CANARY -> PRODUCTION
```

`VALIDATED` verlangt jeweils neue `BACKTEST`-, `VALIDATION`- und
`OUT_OF_SAMPLE`-Evidenz. Holdout-Daten dürfen erst in `VALIDATED` ausgewertet
werden. Anschließend werden `SHADOW`, `PAPER` und `CANARY` nur in ihrem jeweils
aktiven Zustand gesammelt. Für jede relevante Stufe gelten mindestens 100
Trades und zwei Symbole; für `VALIDATED` zusätzlich zwei Timeframes. Jede
Slice muss profitabel sein, Profit Factor mindestens 1,2, Drawdown höchstens
15 % und der größte realisierte Tagesverlust höchstens 10 USDT.

Eine einzelne Evidenzzeile sollte immer eine einmalige Evidence-ID, einen
SHA-256 des Datensatzes und Provenance-JSON erhalten. Die CLI kann diese drei
Felder aus Kompatibilitätsgründen auslassen und erzeugt dann nur eine
deterministische ID; das ist schwächere, nicht unabhängig attestierte Evidenz.
`--max-daily-loss-abs` und alle Kennzahlen sind dagegen zwingend. Das
vollständige, aktuelle Argumentformat liefert:

```powershell
& .\.venv\Scripts\python.exe -m local_trader evaluate --help
& .\.venv\Scripts\python.exe -m local_trader promote --help
```

Die Registry prüft die Reihenfolge und weist identische Evidenzzeilen ab. Die
Kennzahlen werden jedoch vom aufrufenden Prozess gemeldet und sind deshalb ohne
Rohdatenreview oder signierte Provenance kein unabhängiger Beweis.

## 3. Exakte promotete Kopie anlegen

Nur eine Datei unter `strategies/promoted/` kann später überhaupt für einen
Live-Recovery-Start autorisiert werden. Sie muss bytegenau einer bereits
registrierten Kandidatenversion entsprechen. Zuerst wird das Laufzeitmanifest
erzeugt:

```powershell
$promotedPath = Join-Path $PWD "runtime\user_data\strategies\promoted\MyStrategy.py"
if (Test-Path -LiteralPath $promotedPath) {
  throw "Promoted target already exists: $promotedPath"
}
Copy-Item -LiteralPath $candidate -Destination $promotedPath
$promoted = Resolve-Path $promotedPath
if ((Get-FileHash $candidate -Algorithm SHA256).Hash -cne
    (Get-FileHash $promoted -Algorithm SHA256).Hash) {
  throw "Candidate/promoted hash mismatch"
}
$manifest = .\runtime\scripts\deployment-manifest.ps1 `
  -StrategyPath $promoted `
  -StrategyName MyStrategy | ConvertFrom-Json
$metadata = $manifest.metadata | ConvertTo-Json -Compress -Depth 5

$promotedRegistration = & .\.venv\Scripts\python.exe -m local_trader --db $db register `
  --name MyStrategy `
  --source $promoted `
  --parent-version $candidateVersion `
  --metadata-json $metadata | ConvertFrom-Json
$promotedVersion = [int]$promotedRegistration.version.version
```

`--parent-version` bezeichnet die passende Kandidatenversion. Ein anderer Hash,
ein Parent aus dem Promoted-Verzeichnis oder ein unvollständiges Manifest wird
abgewiesen. Die promotete Version beginnt bewusst als frische `IDEA` mit null
Evidenzen, Trials und Promotionsereignissen; nichts wird vom Kandidaten geerbt.
Alle Gates müssen für `$promotedVersion` ab `IDEA` erneut mit
`--version $promotedVersion` durchlaufen werden.

## 4. Echtgeld bleibt ein separater menschlicher Vorgang

Der MCP-Server darf höchstens bis `PAPER` promoten. `CANARY` und `PRODUCTION`
verlangen die konkrete Versionsnummer, ein echtes interaktives Terminal und
eine maximal 15 Minuten gültige Einmaldatei außerhalb der Candidate- und
Promoted-Verzeichnisse. Diese Datei wird beim Erfolg atomar konsumiert: Der
ursprüngliche Pfad verschwindet und wird durch einen Marker mit dem Suffix
`.consumed.<sha256>` ersetzt. Dieser Marker gehört zum Auditnachweis und darf
nicht gelöscht oder verändert werden, solange `authorize` oder ein
Recovery-Start möglich bleiben soll.

Die Einmaldatei enthält exakt diese Felder (Zeit und Hash durch die tatsächlich
geprüften Werte ersetzen):

```json
{"strategy":"MyStrategy","version":2,"target":"CANARY","artifact_sha256":"64 lowercase hex characters","approver":"Human Name","expires_at":"2026-08-12T20:00:00Z"}
```

Der folgende Aufruf muss direkt in einem echten PowerShell-Terminal erfolgen;
Umleitung, Pipe, MCP oder ein nicht-interaktiver Agent werden abgewiesen:

```powershell
& .\.venv\Scripts\python.exe -m local_trader --db $db promote `
  --strategy MyStrategy `
  --version $promotedVersion `
  --to CANARY `
  --manual-approval `
  --approved-by "Human Name" `
  --approval-file C:\secure\local-trader-canary-approval.json

& .\.venv\Scripts\python.exe -m local_trader --db $db authorize `
  --strategy MyStrategy `
  --version $promotedVersion `
  --target CANARY
```

Bei Erfolg liefert `authorize` unter `authorization` mindestens Strategie,
Version, Zielstufe, Lifecycle, promovierten Source-Pfad, Artefakt-Hash und
-größe, RiskPolicy, Metadaten und Deployment-Manifest. Der Launcher verwendet
genau dieses Objekt und prüft Pfad und Hash danach nochmals. Ein Lifecycle-,
Integritäts-, Manifest-, Hash- oder Approval-Fehler beendet den Befehl mit
Exitcode ungleich null.

Für `PRODUCTION` ist nach echter neuer CANARY-Evidenz eine zweite, eigene
Einmaldatei mit `target=PRODUCTION` und ein neuer interaktiver Promote-Aufruf
nötig.

Auch eine bestandene Registry-Promotion reicht nicht: Der exakte Hash muss
zusätzlich nach einem unabhängigen manuellen Source-Audit als `APPROVED` in
`runtime/trusted-live-artifacts.json` stehen. Diese Liste ist derzeit leer,
beide vorhandenen Strategien sind negativ, und der Live-Launcher kann daher
kein Artefakt starten.
