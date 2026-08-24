# AI Trading Agent – lokaler V12.31-Zehn-Paare-Testbot

Deutscher Einstieg und aktueller Projektstatus: [`START_HERE_DE.md`](START_HERE_DE.md).

Dieses Repository enthält den lokalen Freqtrade-/Binance-Testbot, seine
Sicherheitsverträge sowie die Werkzeuge für Backtest, Replay, Audit und
reproduzierbare Research-Prüfungen. Der aktive Testbot lädt
`CompressionBreakout250` / V12.31 ausschließlich im Paper-/Dry-run-Modus.

## Aktueller Betriebsrahmen

- Branch: `agent/v12-17-ten-pair-research-ui`
- Binance Spot: BTC, ETH, SOL, XRP, BNB, DOGE, LINK, TRX, LTC und BCH gegen
  USDT
- long-only, 1x, ausschließlich virtuelles Kapital
- 250 USDT Startkapital, maximal 80 USDT je Position
- maximal drei Positionen beziehungsweise 240 USDT Gesamtengagement
- kein Futures, Margin, Short, Hebel, DCA, Martingale oder automatische
  Echtgeld-Freigabe

V12.18 reparierte den begonnenen Zehn-Paare-Ausbau von V12.17. V12.19
beschleunigte den detailgenauen Backtest und machte den Zehner-Einzelbatch
fortsetzbar. V12.20 sperrte nach vollständiger Zehn-Paare-Diagnose schädliche
Zusatzblöcke pair-lokal. V12.22 ergänzte für SOL einen 4h-ADX von mindestens
21. V12.31 behält dies und DOGEs kausal ausgewählten 4h-Supertrend(20, 3)
oberhalb einer steigenden EMA100. Zusätzlich kombiniert sie einmalig die
unveränderte, zuvor separat geprüfte BCH-EMA30/EMA80-Route oberhalb einer
steigenden EMA100 bei ADX mindestens 24.
Alle zehn Märkte
konkurrieren im Paperbot und im maßgeblichen Portfoliobacktest um dasselbe
250-USDT-Wallet. Je Trade beginnt der Bot mit 80 USDT. Nur BTC, ETH, LINK und
TRX dürfen höchstens zwei weitere 80-USDT-Stufen ergänzen. Eine Ergänzung ist
nur erlaubt, wenn der Trade
bereits im Gewinn liegt, der aktuelle Einstieg ebenfalls profitabel ist und
der neue Preis über allen bisherigen Einstiegen liegt. Das ist
Gewinner-Pyramiding und ausdrücklich kein DCA oder Verlust-Nachkaufen.

Die pair-spezifischen V12.15-Kerne, BTC-/ETH-Reclaims, Stopps und
Verlustcluster-Sperren bleiben erhalten. LINK, TRX und LTC werden weiterhin
mit klar gekennzeichneten, noch nicht als Champion akzeptierten Profilen
gemessen. Ein gutes Ergebnis eines einzelnen Coins ersetzt nicht den gemeinsamen
Zehn-Paare-Portfoliotest.

Der V12.12-Drei-Jahres-Lauf bleibt als starke, aber formal am
ersten nativen Candle-Dateiaudit gescheiterte Diagnose dokumentiert. Er wird
nicht verschwiegen, nicht als vollständig bestanden bezeichnet und durch seinen
versionierten Fingerabdruck nicht identisch wiederholt.
V12.13 und V12.14 sind als verworfene Versuche dokumentiert. V12.15 bleibt die
akzeptierte Sechs-Paare-Referenz. V12.16 (ADA) und die fehlerhafte erste
V12.17-Umsetzung bleiben als nicht 1:1 zu wiederholende Evidenz erhalten.
V12.31 ist der aktive, vorab registrierte Paper-/Dry-run-Kandidat. Sein exakter
gemeinsamer Drei-Jahres-Test endete bei 669,857 USDT aus 250 USDT, mit PF 2,4358
und 12,5447 Prozent geschlossenem Drawdown. DOGE reproduzierte einzeln
+112,552 USDT; BCH reproduzierte +25,398 USDT und blieb im jüngsten Jahr sowie
bei erhöhten Gebühren positiv. Frische Paper-Evidenz steht noch aus; SOL und
LTC bleiben im gemeinsamen Test negativ und das langfristige Ziel je Coin ist
noch nicht erreicht.

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

Der UI-Backtest bietet zwei klare Aktionen: einen ausgewählten Coin mit eigenem
250-USDT-Testwallet testen oder mit `Alle 10 einzeln testen` automatisch zehn
getrennte 250-USDT-Läufe nacheinander ausführen. Der Zehner-Batch läuft auf dem
lokalen Server weiter, wenn die Backtest-Seite geschlossen oder neu geladen
wird, und schreibt nach jedem Coin Plan, Ergebnis, Laufzeit und den Vergleich
zum vorherigen materiell anderen Lauf. Der gemeinsame Portfolio-Lauf
bleibt als interner Replay-/Audit-Pfad erhalten und ist kein normaler UI-Knopf.
Jeder Lauf protokolliert außerdem die tatsächlich
geöffnete Strategie und Konfigurationskette sowie die nativen Candle-Ladevorgänge
mit Datei-Hash und bricht bei einer
unerwarteten Repo-Datei oder einem Kindprozess ab.

## Research und Sicherheit

Die getrennte Deep-Research-Uebergabe fuer alle zehn Coins liegt unter
[research/deep_research_10_coins/README_DE.md](research/deep_research_10_coins/README_DE.md).
Sie verhindert eine Einheitsstrategie, trennt Einzelwallet und gemeinsames
3x80-USDT-Portfolio und fuehrt angenommene sowie verworfene Pair-Versuche auf.

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
- [`research/V12_18_REPAIR_HANDOFF_DE.md`](research/V12_18_REPAIR_HANDOFF_DE.md)
- [`research/V12_19_PERSISTENT_PAIR_LEARNING_DE.md`](research/V12_19_PERSISTENT_PAIR_LEARNING_DE.md)
- [`research/V12_20_SELECTIVE_PYRAMID_DE.md`](research/V12_20_SELECTIVE_PYRAMID_DE.md)
- [`research/V12_22_SOL_ADX21_DE.md`](research/V12_22_SOL_ADX21_DE.md)
- [`research/V12_30_DOGE_SUPERTREND_DE.md`](research/V12_30_DOGE_SUPERTREND_DE.md)
- [`research/V12_31_DOGE_BCH_COMBINATION_DE.md`](research/V12_31_DOGE_BCH_COMBINATION_DE.md)

Herkunft und Lizenzgrenzen der verbliebenen MIT-lizenzierten Research-Rollen
sind in [`docs/UPSTREAM.md`](docs/UPSTREAM.md), [`LICENSE`](LICENSE) und
[`NOTICE.md`](NOTICE.md) dokumentiert. Backtests und Paper-Trading garantieren
keine zukünftige Rendite.
