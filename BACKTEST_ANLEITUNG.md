# Backtest in der Testbot-Oberfläche

## Maßgeblicher Grundsatz

Der UI-Backtest verwendet **keine separate Backtest-Strategie**. Für jeden Lauf wird die tatsächlich aktive Datei

`runtime/user_data/strategies/CompressionBreakout250.py`

neu gehasht und über den gesperrten Freqtrade-Backtestpfad geladen.

Auf dem aktuellen V12-Research-Zweig ist die aktive Strategy-Quelle weiterhin **V11**. V12 selbst ist Research-Infrastruktur und verändert den Hotpath nicht automatisch.

## Auswahl

Im UI können einzeln getestet werden:

- BTC/USDT
- ETH/USDT
- SOL/USDT
- 1, 2 oder 3 Jahre

Jedes Pair wird mit **seinen eigenen Daten** getestet. Der aktuelle V11-Pfad injiziert kein BTC-Regime in ETH oder SOL.

## Benötigte Daten

Für das ausgewählte Pair werden benötigt:

- 15m – Strategie-/Signal-Timeframe
- 1m – Detail-Timeframe für realistischere Intracandle-Simulation
- 1h – informatives Pair-Timeframe
- 4h – informatives Pair-Timeframe

Vor dem Lauf werden Daten aktualisiert und fehlende ältere Bereiche mit dem Freqtrade-Prepend-Pfad ergänzt.

Der Lauf bricht fail-closed ab, wenn Daten fehlen, Zeitstempel nicht monoton sind, Duplikate/Lücken vorhanden sind oder das benötigte Fenster nicht vollständig abgedeckt ist.

## Backtestparameter

Der normale UI-Backtest verwendet:

- 250 USDT Startkapital
- die aktuell konfigurierten Positions-/Stake-Grenzen
- `--fee 0.002` je Orderseite
- `--timeframe-detail 1m`
- `--cache none`
- die aktuellen Strategy-/Protection-Regeln

Resultate werden getrennt unter `runtime/user_data/backtest_results/ui/<Run-ID>/` abgelegt.

Angezeigt werden unter anderem:

- Netto-USDT-Gewinn/-Verlust
- Rendite
- Endkapital
- Tradezahl
- Profit Factor
- Winrate
- Max Drawdown
- tatsächlicher Backtestzeitraum
- Candle-Integritätsstatus

## Was ein Backtest nicht beweist

Ein historischer OHLCV-Backtest rekonstruiert weder historische Orderbuch-Warteschlangen noch echte Netzwerklatenz oder Tick-für-Tick-Ausführung. Das 1m-Detail verbessert die Simulation, ersetzt diese Informationen aber nicht.

Deshalb bleibt der normale Backtest ein wichtiger, aber nicht allein ausreichender Research-Beweis. Robuste Kandidaten müssen zusätzlich gegen zeitliche Slices, Kostenstress, Walk-Forward/Blind-Evidenz und – wenn relevant – Replay-/Execution-Stress geprüft werden.

## V12-Research

Die V12-Optimizer/Family-League-Runs dienen der schnellen Kandidatensuche. Ein dort gefundener Gewinner ist **noch nicht automatisch die aktive Strategy**. Erst ein ausdrücklich promovierter Kandidat wird in die aktive Strategy-Datei übernommen und anschließend mit dem exakten lokalen Freqtrade-Backtest gegengeprüft.

Kein Backtestpfad darf Echtgeldorders senden.
