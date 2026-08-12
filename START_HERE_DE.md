# Start hier: lokaler Binance-Forschungsbot

## Testbot per Doppelklick

Für den ausschließlich simulierten Dauer-Test mit 250 virtuellen USDT genügt
ein Doppelklick auf `STARTBOT.bat`. Installation, Bedienung, Stoppschalter und
Auswertungsdateien erklärt [`TESTBOT_ANLEITUNG.md`](TESTBOT_ANLEITUNG.md).

## Ergebnis und aktueller Freigabestatus

Die im Video gezeigte Forschungsarchitektur ist lokal nachgebaut: mehrere
Rollen erzeugen Hypothesen, Freqtrade prüft Strategien reproduzierbar, und eine
unveränderliche Registry erzwingt die Reihenfolge von Research bis Production.
Der öffentliche DaviddTech-Code liefert nur Prompts und Rollen, keinen
ausführbaren Trading-Bot und nicht den proprietären Trader-Dev-Server. Deshalb
wurde die fehlende Laufzeit mit Freqtrade 2026.7 ergänzt.

**Echtgeld ist derzeit vollständig gesperrt.** Beide bislang geprüften
Strategien verloren Geld und wurden verworfen:

- `CompressionBreakout250`: −40,22 % im Gesamtzeitraum und −18,46 % im Holdout.
- `TrendPullback250V1`: −17,90 % im Training und −11,71 % im Holdout.

Die Source-Audit-Liste `runtime/trusted-live-artifacts.json` enthält deshalb
keinen freigegebenen Hash. Der Live-Launcher kann aktuell kein Artefakt starten.
Das ist die korrekte Schutzentscheidung, kein Installationsfehler.

## 1. Einmalig installieren

```powershell
Set-Location "C:\Dev\DaviddTech\ai-trading-agent"
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\scripts\setup-venv.ps1
```

Das verlangt `uv`, erzeugt `.venv` im Repository und synchronisiert die exakt
in `uv.lock` gepinnten Pakete für Freqtrade, Registry, MCP, Tests und Ruff im
`--frozen`-Modus.

## 2. Sicherheitsverträge prüfen

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
& .\.venv\Scripts\ruff.exe check src tests research runtime
```

## 3. Registry

Die lokale Registry wurde bereits als leere Schema-v4-Datenbank initialisiert.
Auf einer neuen Installation geschieht das einmalig mit:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\research\Initialize-Registry.ps1
```

Sie liegt unter `research/registry/strategies.sqlite3` und wird nicht in Git
aufgenommen. Jede Version bindet den exakten Python-Hash. Erst eine separate,
bytegleiche Version im Promoted-Verzeichnis muss zusätzlich die wirksame
Live-Konfiguration, `uv.lock`, lokale Imports und Freqtrade 2026.7 binden. Neue
Strategieänderungen werden immer als neue Version registriert.

Der genaue, absichtlich manuelle Ablauf von Kandidat, Evidenz, identischer
promoteter Kopie und Einmalfreigabe steht in
[`docs/REGISTRY_WORKFLOW_DE.md`](docs/REGISTRY_WORKFLOW_DE.md). Eine promotete
Kopie beginnt als frische `IDEA`; Messwerte und Freigaben werden nie von einer
Kandidatenversion geerbt.

Die optionale MCP-Schicht enthält nur Forschungstools und keine Order-, Secret-
oder Live-Start-Funktion:

```powershell
# Nur Vorschau
powershell -NoProfile -ExecutionPolicy Bypass -File .\research\Install-LocalMcp.ps1

# Erst dieser Aufruf ändert die lokale Codex-Konfiguration
powershell -NoProfile -ExecutionPolicy Bypass -File .\research\Install-LocalMcp.ps1 -Install
```

## 4. Marktdaten und Analysen reproduzieren

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\scripts\download-data.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\scripts\backtest.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\scripts\lookahead-analysis.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\scripts\recursive-analysis.ps1
```

Backtest und Lookahead rechnen mit 0,2 % Kosten je Orderseite als vorsichtigem
Proxy für 0,1 % Gebühr plus 0,1 % Slippage. Daten und Ergebnisarchive bleiben
lokal und sind von Git ausgeschlossen. Die vollständigen Messwerte stehen in
`docs/LOCAL_VALIDATION.md`.

## 5. Forschungsplan anzeigen

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\research\Start-ResearchDesk.ps1 -Status
```

Autonome `-Once`- und `-Daemon`-Zyklen sind in diesem Checkout hart deaktiviert.
`workspace-write` verhindert Schreibzugriffe außerhalb des Staging-Verzeichnisses,
aber keine Lesezugriffe desselben Windows-Benutzers auf den echten Holdout oder
andere Credential-Dateien. Eine scheinbare Prompt-Quarantäne wäre deshalb nicht
ehrlich. Die vorbereitete Scheduler-Logik darf erst in einem separaten
Low-Privilege-Konto, einer VM oder einem Container aktiviert werden, der nur die
Staging-Daten sieht und den gesamten Prozessbaum zuverlässig beendet.

## 6. Dry-run

Ein Integrationsstart bleibt standardmäßig `stopped`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\scripts\start-dryrun.ps1
```

Simulierte Entries werden ausschließlich über `STARTBOT.bat` aktiviert. Der
frühere direkte Schalter `start-dryrun.ps1 -EnableEntries` ist gesperrt, damit
niemand den Doppelstart-Lock und die Sitzungsprotokollierung umgeht. Dieser
technische Forward-Test der vorhandenen Baseline ist keine Promotion: Die
Strategie ist historisch negativ, bleibt für Echtgeld gesperrt und der Test
darf nicht als Profitabilitätsnachweis verstanden werden.

## 7. Warum Echtgeld noch nicht startet

Ein späterer, rein pausierter Recovery-Start verlangt gleichzeitig:

1. stufenspezifische positive Evidenz bis `CANARY` oder `PRODUCTION`;
2. eine interaktive, maximal 15 Minuten gültige Einmalfreigabe für den exakten
   Strategie-Hash;
3. ein Manifest mit Hashes von Strategie, wirksamer Konfiguration, `uv.lock`
   und lokalen Imports;
4. einen separaten manuellen Source-Audit desselben Hashes;
5. `user_data/STOP_ENTRIES`, einen exklusiven Instanz-Lock und einen Start im
   Zustand `paused`.

Der pausierte Launcher verwaltet nur bestehende Positionen und Schutzorders;
er besitzt keinen Schalter für neue Echtgeld-Entries. Generierter Python-Code
wird nie allein aufgrund guter Backtest-Zahlen mit Exchange-Credentials
ausgeführt.

Für eine spätere Echtgeldphase gelten zusätzlich außerhalb der Software:

- eigenes Binance-Konto oder Subkonto mit höchstens 250 USDT;
- API-Key nur für Lesen und Spot-Handel;
- Auszahlungen, Transfers, Margin und Futures deaktiviert;
- IP-Allowlist;
- Secrets nur als Prozessvariablen, nie in Chat, JSON, Code oder Git;
- höchstens drei Positionen à 80 USDT, 240 USDT Gesamtengagement, 1x, Long-only.

Es gibt keine garantierte Rendite. Auch ein positiver Backtest wäre nur ein
Grund für weitere Forward- und Canary-Prüfung, kein Gewinnbeweis.
