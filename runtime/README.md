# Freqtrade-Laufzeit: 250 USDT, Binance Spot

Diese Laufzeit ist eine vorsichtige Forschungs- und Integrationsbasis, kein
Renditeversprechen. Sie ist auf Freqtrade `2026.7` festgesetzt und nutzt nur
`BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `XRP/USDT`, `BNB/USDT` und `DOGE/USDT`
auf Binance Spot.

Der Doppelklick-Ablauf für den ausschließlich simulierten 24/7-Test,
einschließlich Stoppschalter, persistenter Datenbank und Auswertung, steht in
[`../TESTBOT_ANLEITUNG.md`](../TESTBOT_ANLEITUNG.md).

## Feste Risikogrenzen

- 250 USDT maximales Botkapital
- maximal drei Positionen à 80 USDT, zusammen höchstens 240 USDT
- Long-only, Spot, 1x; kein Margin, Futures, Short, DCA oder Martingale
- neue Entries werden nach 10 USDT realisiertem Tagesverlust gesperrt
- Stop-Loss −5,5 %, auf der Börse als Stop-Limit
- `emergency_exit` und `force_exit` als Market-Order
- API, Telegram, Webhook und externer Message-Consumer deaktiviert
- statische Paarliste und Entry-Kill-Switch

`config.json` ist Dry-run und startet `stopped`. Das Live-Overlay startet
dagegen `paused`: Freqtrade verwaltet in diesem Zustand vorhandene Ausstiege
und Schutzorders, eröffnet aber keine Positionen. Im Live-Overlay ist
`cancel_open_orders_on_exit=false`, damit ein Recovery-Start vorhandene
Schutzorders nicht automatisch storniert.

Ein Stop-Limit kann bei einem Kurs-Gap ungefüllt bleiben. Auch die konservative
Konfiguration beseitigt Markt-, Börsen-, Netzwerk- und Softwarefehler nicht.
Die Tagesverlustlogik ist eine Entry-Sperre, keine garantierte harte
Verlustobergrenze: offene Verluste, Gaps und Slippage können den Betrag
überschreiten.

## Aktive Dry-run-Strategie

Der Testbot lädt `CompressionBreakout250` / V12.15. Die Strategie verwendet
pair-spezifische langsame Donchian-/Trendprofile. BTC und ETH besitzen zusätzlich
ihre separat markierten EMA20-Trend-Reclaims innerhalb eines bestätigten
1h/4h-Aufwärtstrends. SOL, XRP, BNB und DOGE bleiben beim bereits vorhandenen
breiten Donchian-Kern. Eine pair-lokale `LowProfitPairs`-Protection pausiert das
betroffene Pair nach zwei unprofitablen Trades für 72 Stunden. Nur ein
Champion-Trade, der bereits mindestens +30 % erreicht hat, erhält einen
+5-%-Gewinnboden.

Zusätzliche Runtime-Callbacks arbeiten fail-closed:

- `custom_stake_amount()` gibt bei Fehlern 0 zurück und kappt auf 80 USDT.
- `confirm_trade_entry()` lehnt falsches Produkt, Paar, Orderart, mehr als drei
  Positionen, mehr als 240 USDT Exposition, den Kill-Switch und Datenbankfehler
  ab.
- `bot_start()` bricht bei abgeschwächtem Stop-Loss, Ordertypen,
  `unfilledtimeout`, Kapital-, Paar-, Spot-, API- oder PAUSED-Vertrag ab.

V12.15 ist ein Research-/Paper-Kandidat und nicht für Echtgeld freigegeben. Die
eingefrorene V8-Baseline unter `../research/baselines/V8/` bleibt separat für
Replay und Audit erhalten. Sicherheitsprüfungen ersetzen keine positive
Erwartung.

## Installation

Im Repository-Stamm:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\scripts\setup-venv.ps1
```

Die native `.venv` enthält Freqtrade, Registry, MCP, pytest und Ruff. Docker ist
optional in `docker-compose.yml` ebenfalls auf 2026.7 gepinnt; die nativen
PowerShell-Skripte sind der hier geprüfte Pfad. Das Setup verlangt `uv` und
synchronisiert mit `--frozen --all-extras`; ein nachfolgender Check muss die
installierte Umgebung als exakt zu `uv.lock` passend bestätigen.

## Daten und Analysen

```powershell
.\runtime\scripts\download-data.ps1 -Days 730
.\runtime\scripts\backtest.ps1 -Timerange "20240812-"
.\runtime\scripts\lookahead-analysis.ps1 -Timerange "20240812-20260812"
.\runtime\scripts\recursive-analysis.ps1 -Timerange "20240812-20260812"
```

Analyse- und Dry-run-Skripte laden zusätzlich `config-public.json`. Es setzt
CCXTs internen `apiKey` auf `null`, damit ausschließlich öffentliche
Binance-Endpunkte genutzt werden. Der Live-Launcher lädt dieses Overlay nie.
`config-analysis.json` ist nur für Freqtrades Lookahead-Diagnose bestimmt.

Backtest und Lookahead verwenden `--fee 0.002` je Seite als Proxy für Gebühr
plus Slippage. Reale Kosten können höher sein. Ein sauberer Lookahead-Bericht
beweist weder Profitabilität noch vollständige Bias-Freiheit.

Der UI-Modus `Gesamtportfolio` simuliert alle sechs Pairs gemeinsam mit genau
einem 250-USDT-Wallet und den bestehenden Positionsgrenzen. Die Einzelpaar-
Läufe dienen der Attribution. Ergebnis und Gesamtauswertung weisen zusätzlich
Kapitalzeit-Nutzung, Zeit ohne Position sowie durchschnittlich und maximal
gleichzeitig offene Positionen aus.

Alle automatisch erzeugten Runtime-Dateien liegen unter `user_data/`: Daten in
`data/`, UI-Backtests in `backtest_results/`, Sitzungsberichte in
`logs/sessions/`, Paper-/Replay-Evidenz in `paper_telemetry/` beziehungsweise
`replay_results/`. Diese Pfade sind von Git ausgeschlossen. Wegwerfbarer
Python-Bytecode-Cache wird in den Startpfaden deaktiviert, sodass der
Repository-Stamm frei von Laufzeitartefakten bleibt. Die dort beim Setup
erzeugte `.venv/` ist die notwendige gelockte Python-/Freqtrade-Umgebung und
kein Bot-Ergebnis.

`backtest_history_analysis.py` liest alle erhaltenen UI-Backtest-ZIPs, markiert
abgebrochene Versuche getrennt und erneuert `GESAMTAUSWERTUNG.md` sowie
`gesamt-auswertung.json`. Rohresultate werden dabei niemals gelöscht;
überlappende Testfenster werden nicht als eine gemeinsame Kapitalkurve
ausgegeben. Portfolio-Läufe werden getrennt von der historischen
historischen Sechs-Zellen- beziehungsweise aktuellen Zwölf-Zellen-
Einzelpaar-Matrix ausgewertet. Jeder neue Lauf muss zusätzlich seinen
Dateizugriffsaudit bestehen.

## Dry-run

```powershell
# Keine simulierten Entries
.\runtime\scripts\start-dryrun.ps1

# Simulierte Entries nur ueber den gesicherten Doppelklick-Pfad
.\STARTBOT.bat
```

`STARTBOT.bat` setzt immer `dry_run=true`; geerbte
`FREQTRADE__...`-Overrides werden abgelehnt. Der frühere direkte Schalter
`start-dryrun.ps1 -EnableEntries` ist gesperrt, damit der exklusive
Doppelstart-Lock nicht umgangen werden kann. Der aktuelle Doppelklick-Test des
V12.15-Kandidaten ist keine Freigabe für Echtgeld.

## Kill-Switch

```powershell
New-Item -ItemType File .\runtime\user_data\STOP_ENTRIES
```

Die Datei blockiert neue Entries, schließt aber keine Position. Entfernen darf
man sie erst nach bewusster Prüfung; der pausierte Live-Launcher verlangt, dass
sie vorhanden ist. `AI_TRADING_KILL_SWITCH_FILE` kann in allgemeinem Dry-run
einen anderen Pfad wählen, wird beim Live-Start aber nicht vom Aufrufer
akzeptiert.

## Deployment-Manifest

Nach einem manuellen Codeaudit lässt sich das deterministische Manifest eines
promoteten Kandidaten anzeigen:

```powershell
.\runtime\scripts\deployment-manifest.ps1 `
  -StrategyPath .\runtime\user_data\strategies\promoted\MyStrategy.py `
  -StrategyName MyStrategy
```

Es bindet den Strategie-Hash, die kanonische wirksame Konfiguration, `uv.lock`,
das leere lokale Import-Bundle und Freqtrade 2026.7. Die Ausgabe ist nur
Registrierungsmetadatum—kein Audit, kein Gate-Ergebnis und keine
Handelserlaubnis.

## Pausierter Live-Recovery-Pfad

Aktuell enthält `trusted-live-artifacts.json` keine freigegebenen Artefakte;
der folgende Pfad ist daher bewusst nicht startbar. Später lautet der Aufruf
für eine bereits in der Registry autorisierte Version:

```powershell
$env:FREQTRADE__EXCHANGE__KEY = "..."
$env:FREQTRADE__EXCHANGE__SECRET = "..."
.\runtime\scripts\start-live-paused.ps1 `
  -Strategy MyAuditedStrategy `
  -Version 7 `
  -Target CANARY
```

Der Launcher prüft vor dem finalen Prozess:

1. exakte Registry-Version und Lifecycle;
2. konsumierte menschliche Einmalfreigabe;
3. Datenbankintegrität und Promotionsledger;
4. Strategie-, Konfigurations-, Lock- und Import-Hashes;
5. einen separaten `APPROVED`-Eintrag für denselben Source-Hash;
6. alle festen Runtime- und RiskPolicy-Grenzen;
7. vorhandenen Kill-Switch und exklusiven Instanz-Lock.

Ein benachbartes Freqtrade-Parameter-JSON ist für Live-Stufen verboten und wird
bereits von Registry und Autorisierung abgewiesen. Der Loader kompiliert direkt
die gelockten, hashgeprüften Source-Bytes, durchsucht kein Strategy-Verzeichnis
und lädt unabhängig davon niemals ein Parameter-JSON.
Preflight-Prozesse erben keine Binance-Schlüssel; der finale Freqtrade-Prozess
erhält eine kleine Environment-Allowlist. Die Registry bleibt für eine
Notfall-Degradierung beschreibbar.

Der Launcher erzwingt immer `paused` und bietet **keinen** Schalter für
Echtgeld-Entries. Arbiträrer generierter Python-Code ist keine sichere
Ausführungsgrenze: Erst ein unabhängiger manueller Source-Audit darf einen
exakten Hash in `trusted-live-artifacts.json` aufnehmen. Wer Schreibzugriff auf
Repository, Registry oder Betriebssystemkonto hat, bleibt Teil der lokalen
Vertrauensgrenze.

Ein Audit-Eintrag hat exakt diese Bedeutung (Werte nur nach tatsächlicher
Codeprüfung einsetzen):

```json
{
  "strategy": "MyAuditedStrategy",
  "artifact_sha256": "64 lowercase hex characters",
  "decision": "APPROVED",
  "reviewed_by": "human reviewer name",
  "reviewed_at_utc": "YYYY-MM-DDTHH:MM:SSZ"
}
```

Das Bearbeiten dieser Datei ist selbst eine privilegierte, menschliche
Betriebsentscheidung und darf niemals ein Research-Agent übernehmen.

Für Binance muss zusätzlich ein eigenes Konto/Subkonto mit höchstens 250 USDT
und einem Key ohne Auszahlung, Transfer, Margin oder Futures verwendet werden;
eine IP-Allowlist ist dringend empfohlen.

## Verifikation

```powershell
& .\.venv\Scripts\python.exe -m pytest tests\runtime -q
& .\.venv\Scripts\ruff.exe check runtime tests\runtime
```

Referenzen: [Freqtrade](https://www.freqtrade.io/en/stable/),
[Lookahead Analysis](https://www.freqtrade.io/en/stable/lookahead-analysis/),
[Recursive Analysis](https://www.freqtrade.io/en/stable/recursive-analysis/).
