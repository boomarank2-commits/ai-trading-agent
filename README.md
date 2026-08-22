# AI Trading Agent – lokaler V12.12-Testbot

Deutscher Einstieg und aktueller Projektstatus: [`START_HERE_DE.md`](START_HERE_DE.md).

Dieses Repository enthält den lokalen Freqtrade-/Binance-Testbot, seine
Sicherheitsverträge sowie die Werkzeuge für Backtest, Replay, Audit und
reproduzierbare Research-Prüfungen. Der aktive Testbot lädt
`CompressionBreakout250` / V12.12 ausschließlich im Paper-/Dry-run-Modus.

## Aktueller Betriebsrahmen

- Branch: `agent/v12-adaptive-league`
- Binance Spot: BTC, ETH, SOL, XRP, BNB und DOGE gegen USDT
- long-only, 1x, ausschließlich virtuelles Kapital
- 250 USDT Startkapital, maximal 80 USDT je Position
- maximal drei Positionen beziehungsweise 240 USDT Gesamtengagement
- kein Futures, Margin, Short, Hebel, DCA, Martingale oder automatische
  Echtgeld-Freigabe

V12.12 verändert keine Signal- oder Exit-Schwelle von V12.9. BTC und ETH
behalten ihren getrennt markierten EMA20-Trend-Reclaim. XRP, BNB und DOGE sind
die einzige neue Strategieänderung und nutzen wie SOL ausschließlich den
bestehenden breiten Donchian-Kern. Alle sechs Märkte verwenden eine pair-lokale
Sperre gegen Verlustcluster.

Der erste gemeinsame V12.12-Drei-Jahres-Lauf ist als starke, aber formal am
ersten nativen Candle-Dateiaudit gescheiterte Diagnose dokumentiert. Er wird
nicht verschwiegen, nicht als vollständig bestanden bezeichnet und durch seinen
versionierten Fingerabdruck nicht identisch wiederholt.

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

Der UI-Backtest bietet zusätzlich eine echte Gesamtportfolio-Sicht: alle sechs
Märkte teilen sich ein 250-USDT-Wallet. Sie ist für Kapitalnutzung und
Portfolioergebnis maßgeblich; die zwölf Einzelpaar-/Zeitraum-Zellen bleiben als
Attribution erhalten. Jeder Lauf protokolliert außerdem die tatsächlich
geöffnete Strategie und Konfigurationskette sowie die nativen Candle-Ladevorgänge
mit Datei-Hash und bricht bei einer
unerwarteten Repo-Datei oder einem Kindprozess ab.

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
