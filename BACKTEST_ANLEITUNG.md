# Backtest in der Testbot-Oberfläche

Der Menüpunkt **Backtest** wird beim normalen `STARTBOT.bat`-Start automatisch in die installierte FreqUI eingeblendet. Er ist Teil des lokalen Testbots und wird aus dem Git-Repository nachinstalliert; ein frischer Clone benötigt keine manuelle Frontend-Anpassung.

Der Backtest ist **keine zweite Trading-Strategie**. Für jeden Lauf wird die aktuell vom Testbot verwendete Datei `runtime/user_data/strategies/CompressionBreakout250.py` neu gehasht und über den gleichen exakten Strategy-Loader geladen. Die normalen `config.json`- und `config-public.json`-Einstellungen bleiben Grundlage des Tests.

In der Oberfläche können aktuell ausgewählt werden:

- BTC/USDT, ETH/USDT oder SOL/USDT;
- 1, 2 oder 3 Jahre historische Daten.

Nach **Backtest starten** lädt Freqtrade öffentliche Binance-Daten für das ausgewählte Pair. Es werden 15-Minuten-Kerzen für die Strategie und zusätzlich 1-Minuten-Kerzen als Detail-Timeframe für realistischere Intracandle-Fills, Stops und Exits geladen. Die Strategie selbst entscheidet weiterhin auf dem aktuell konfigurierten 15-Minuten-Timeframe.

Der Backtest verwendet 250 USDT Startkapital, die aktuellen Schutzregeln und einen konservativen Kostenwert von 0,2 Prozent je Orderseite (`--fee 0.002`). Ergebnisse werden getrennt unter `runtime/user_data/backtest_results/ui/<Run-ID>/` gespeichert.

Angezeigt werden unter anderem:

- Gewinn/Verlust in USDT;
- Rendite in Prozent;
- Endkapital;
- Tradezahl;
- Profit Factor;
- Trefferquote;
- maximaler Drawdown.

Nur ein UI-Backtest kann gleichzeitig laufen. Der laufende 24/7-Dry-run bleibt davon getrennt und handelt weiter mit Testgeld. Der Backtest lädt keine Binance-API-Schlüssel und kann keine Echtgeldorder senden.

Wichtig: Ein Backtest ist ein historischer Freqtrade-Backtest. Er ist für schnelle Prüfung des aktuellen Bot-Codes gedacht. Der in `CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md` beschriebene streng chronologische historische Live-Replay/Zeitmaschinen-Modus ist eine spätere, zusätzliche Validierungsstufe und darf nicht mit diesem schnellen Backtest verwechselt werden.
