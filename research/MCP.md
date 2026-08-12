# Lokale Research-MCP-Schnittstelle

Die lokale MCP-Schicht verbindet Codex per `stdio` mit der SQLite-Registry. Sie
ist absichtlich **keine Trading-Schnittstelle**: Es gibt keine Tools für Binance,
Orders, Zugangsdaten, Bot-Start/-Stop oder Live-Ausführung.

Verfügbar sind ausschließlich strukturierte Registry-Operationen:

- Konfiguration und Datenbankintegrität anzeigen
- Strategien auflisten und Status/Evidenz lesen
- SHA-256-Artefakte prüfen und neue Kandidaten registrieren
- Backtest-, Holdout-, Shadow- und Paper-Metriken erfassen
- Research-Promotions prüfen und schrittweise bis maximal `PAPER` ausführen

`CANARY` und `PRODUCTION` werden in der MCP-Schicht vor jedem Promotion-Aufruf
abgelehnt. Die MCP-Promotion besitzt weder ein Feld für manuelle Freigaben noch
für einen menschlichen Freigeber. Eine spätere Live-Freigabe bleibt damit ein
separater, ausdrücklich menschlicher CLI-Prozess.

## 1. Registry einmalig initialisieren

Vom Repository-Stamm aus:

```powershell
$db = Join-Path $PWD "research\registry\strategies.sqlite3"
$candidateRoot = Join-Path $PWD "runtime\user_data\strategies\candidates"
$promotedRoot = Join-Path $PWD "runtime\user_data\strategies\promoted"

& .\.venv\Scripts\python.exe -m local_trader --db $db init `
  --candidate-root $candidateRoot `
  --promoted-root $promotedRoot
```

Die Registry und promoteten Artefakte sind lokale Laufzeitdaten und werden von
Git ignoriert. Manuell geprüfte Kandidaten dürfen dagegen bewusst versioniert
werden, damit Fehlversuche und Reviews nachvollziehbar bleiben. Niemals
API-Schlüssel, Secrets oder Passwörter in Beschreibungen, Notizen oder Metadaten
speichern; die MCP-Schicht weist
offensichtliche Secret-Felder zusätzlich zurück und redigiert solche Felder in
Antworten.

## 2. Codex-Konfiguration bewusst registrieren

Das Installationsskript verändert standardmäßig nichts. Es zeigt zuerst nur den
vollständig aufgelösten `codex.cmd mcp add`-Befehl:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\research\Install-LocalMcp.ps1
```

Erst mit `-Install` wird genau dieser MCP-Eintrag geschrieben:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\research\Install-LocalMcp.ps1 -Install
```

Eine andere Registry kann explizit angegeben werden:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\research\Install-LocalMcp.ps1 `
  -Database "C:\voller\Pfad\registry.sqlite3" -Install
```

Das Skript startet keinen Bot und installiert nichts auf Binance. Es registriert
nur den lokalen Python-`stdio`-Prozess unter dem Namen `local-trader`.

## Direkter Start ohne Codex-Konfigurationsänderung

Für einen MCP-Client kann der Datenbankpfad alternativ über eine dedizierte
Umgebungsvariable gesetzt werden:

```powershell
$env:LOCAL_TRADER_REGISTRY_DB = "C:\voller\Pfad\registry.sqlite3"
& .\.venv\Scripts\python.exe -m local_trader.mcp_server
```

`--db` hat Vorrang vor `LOCAL_TRADER_REGISTRY_DB`. Der Transport ist immer
`stdio`; die Schnittstelle öffnet keinen Netzwerkport.
