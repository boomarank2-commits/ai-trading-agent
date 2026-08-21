# AI Trading Agent – lokaler V12.9-Testbot

Deutscher Einstieg und aktueller Projektstatus: [`START_HERE_DE.md`](START_HERE_DE.md).

Dieses Repository enthält den lokalen Freqtrade-/Binance-Testbot, seine
Sicherheitsverträge sowie die Werkzeuge für Backtest, Replay, Audit und
reproduzierbare Research-Prüfungen. Der aktive Testbot lädt
`CompressionBreakout250` / V12.9 ausschließlich im Paper-/Dry-run-Modus.

## Aktueller Betriebsrahmen

- Branch: `agent/v12-adaptive-league`
- Binance Spot, BTC/USDT, ETH/USDT und SOL/USDT
- long-only, 1x, ausschließlich virtuelles Kapital
- 250 USDT Startkapital, maximal 80 USDT je Position
- maximal drei Positionen beziehungsweise 240 USDT Gesamtengagement
- kein Futures, Margin, Short, Hebel, DCA, Martingale oder automatische
  Echtgeld-Freigabe

V12.9 behält die pair-spezifischen Donchian-Einstiege, ergänzt für BTC und ETH
einen getrennt markierten EMA20-Trend-Reclaim und verwendet eine pair-lokale
Sperre gegen Verlustcluster. SOL nutzt den Reclaim-Challenger nicht.

## Start und Auswertung

- `STARTBOT.bat`: Testbot und lokale Oberfläche starten
- `STOP_NEUE_TESTTRADES.bat`: neue Dry-run-Einstiege sperren
- `TESTTRADES_FREIGEBEN.bat`: Dry-run-Einstiege wieder freigeben
- `TESTBOT_AUSWERTUNG.bat`: Dry-run-Datenbank und sämtliche erhaltenen alten
  sowie neuen UI-Backtests gemeinsam auswerten
- `HISTORISCHER_LIVE_REPLAY.bat`: eingefrorenen V8-Full-System-Replay ausführen

Backtest-Rohdaten bleiben außerhalb von Git unter
`runtime/user_data/backtest_results/`. Die automatische Gesamtauswertung löscht
keinen Lauf, markiert historische 1:1-Doppelläufe und vermischt überlappende
Zeiträume nicht zu einer künstlichen Kapitalkurve. Neue identische UI-Läufe
werden über einen inhaltlichen Fingerabdruck vor dem Start blockiert;
Versions- oder Kommentaränderungen reichen nicht als neuer Versuch.

Der UI-Backtest bietet zusätzlich eine echte Gesamtportfolio-Sicht: BTC, ETH
und SOL teilen sich ein 250-USDT-Wallet. Sie ist für Kapitalnutzung und
Portfolioergebnis maßgeblich; die sechs Einzelpaar-Läufe bleiben als
Attribution erhalten.

## Research und Sicherheit

Der eingefrorene V8-Stand bleibt als Baseline unter `research/baselines/V8/`
erhalten. Historische V8/V9/V10/V11-Ergebnisse sind Evidenz, keine parallel
aktiven Bot-Versionen. Neue Kandidaten müssen die dokumentierten Replay-,
Paritäts-, Ausführungs-, Red-Team- und Statistikprüfungen durchlaufen.

Maßgebliche Dokumente:

- [`RESEARCH_MASTERPLAN_DE.md`](RESEARCH_MASTERPLAN_DE.md)
- [`docs/DEEP_RESEARCH_GAP_AUDIT_DE.md`](docs/DEEP_RESEARCH_GAP_AUDIT_DE.md)
- [`docs/LOCAL_ARCHITECTURE.md`](docs/LOCAL_ARCHITECTURE.md)
- [`docs/LOCAL_VALIDATION.md`](docs/LOCAL_VALIDATION.md)
- [`runtime/README.md`](runtime/README.md)
- [`research/trial_ledger.csv`](research/trial_ledger.csv)

Herkunft und Lizenzgrenzen der verbliebenen MIT-lizenzierten Research-Rollen
sind in [`docs/UPSTREAM.md`](docs/UPSTREAM.md), [`LICENSE`](LICENSE) und
[`NOTICE.md`](NOTICE.md) dokumentiert. Backtests und Paper-Trading garantieren
keine zukünftige Rendite.
