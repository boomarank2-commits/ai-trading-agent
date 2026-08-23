# Backtest in der Testbot-Oberfläche

## Maßgeblicher Grundsatz

Der UI-Backtest verwendet **keine separate Backtest-Strategie**. Für jeden Lauf wird die tatsächlich aktive Datei

`runtime/user_data/strategies/CompressionBreakout250.py`

neu gehasht und über den gesperrten Freqtrade-Backtestpfad geladen.

Auf dem Branch `agent/v12-17-ten-pair-research-ui` ist diese aktive
Strategy-Quelle der **V12.18-Paper-/Dry-run-Kandidat** des Bots. Die eingefrorene
V8-Baseline unter
`research/baselines/V8/` bleibt davon getrennte Replay-/Audit-Evidenz.

## Auswahl

Im UI können getestet werden:

- gemeinsames Portfolio aller zehn Paare mit einem einzigen 250-USDT-Konto
- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- BNB/USDT
- DOGE/USDT
- LINK/USDT
- TRX/USDT
- LTC/USDT
- BCH/USDT
- 1, 2 oder 3 Jahre

Der Gesamtportfolio-Modus ist die maßgebliche Sicht auf die Nutzung der echten
250 USDT: alle zehn Märkte konkurrieren gemeinsam um höchstens drei Entry-Blöcke
zu je 80 USDT. Der UI-Knopf heißt `Alle 10 zusammen`. Die Einzelpaar-Läufe und
der Knopf `10 Einzeltests` sind nur für Attribution und Diagnose; ihre Gewinne
dürfen nicht als gemeinsames Konto addiert werden.

Alle Signale bleiben **pair-lokal**. V12.18 injiziert kein BTC-Regime in andere
Pairs. BTC und ETH behalten ihre markierten Trend-Reclaims; die übrigen acht
Paare handeln den Broad-Core-Donchian-Pfad. Die 72-Stunden-Pairpause nach zwei
unprofitablen Trades und der +5-%-Stopboden nach mindestens +30 % bei
Champion-Trades bleiben erhalten. Ein zweiter oder dritter Block im selben
Trade ist nur bei einem neuen Signal, positivem Trade und einem Kurs über allen
früheren Entry-Fills erlaubt. Verlust-Nachkauf bleibt gesperrt.

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
Die Starter deaktivieren wegwerfbaren Python-Bytecode-Cache, damit keine
`__pycache__`-Ordner neben den Quelldateien entstehen.

## Kein identischer Backtest zweimal

Vor dem Start bildet der Bot einen Fingerabdruck aus Strategy-Logik,
Backtestparametern, sicherheitsrelevanter Konfiguration, Pair, Laufzeit und dem
festen Freqtrade-Protokoll. Gibt es denselben Fingerabdruck bereits, wird der
Lauf **vor** Marktdaten-Download und **vor** Erstellung eines neuen
Ergebnisordners blockiert. Das gilt auch, wenn eine abgeschlossene Simulation
erst an einem technischen Audit-Gate scheiterte. Die Fingerabdrücke werden
zusätzlich in `research/executed_test_fingerprints.csv` versioniert, damit die
Sperre nach einem Git-Pull erhalten bleibt. Änderungen nur an Versionsnummer, Kommentar oder
Beschreibung umgehen die Sperre nicht. In der Zehner-Einzelmatrix werden bestehende
Zellen als „Doppeltest übersprungen“ angezeigt.

Eine neue Strategy muss zuerst genau einmal in `research/trial_ledger.csv`
registriert sein. Für jeden gestarteten neuen Lauf werden automatisch diese
Belege im Run-Ordner und Ergebnis-ZIP gesichert:

- `experiment-plan.json`: Hypothese, Vorgänger, Erfolgskriterium und gesamte
  Experimentkette
- `strategy-change.diff`: exakte Quellcodeänderung gegenüber dem Vorgänger
- `experiment-result.json`: Fingerabdruck, tatsächlicher Ausgang und Kennzahlen
- `file-access-audit.json`: tatsächlich geöffnete Strategy-/Config-Dateien,
  Candle-Ladevorgänge an Freqtrades nativer Arrow-Grenze mit SHA-256 sowie die
  Bestätigung, dass kein Kindprozess gestartet wurde

Der Lauf gilt nur dann als abgeschlossen, wenn die aktive Strategy-Quelle, beide
öffentlichen Config-Dateien und alle erwarteten Candle-Sätze beobachtet und nach
dem Laden unverändert gehasht wurden.
Eine andere Repo-Datei, Candle-Datei eines nicht angeforderten Pairs oder ein
Kindprozess führt zum fail-closed Abbruch.

Neue Marktdaten allein machen keinen neuen identischen UI-Test. Neue Daten
werden im Dry-run als Forward-Evidenz gesammelt. Ein bewusst anderes, vorab
dokumentiertes Testfenster oder Protokoll wäre ein eigenes Experiment.

Nach jedem erfolgreichen Lauf wird zusätzlich die verlustfreie Gesamtauswertung
`runtime/user_data/backtest_results/ui/GESAMTAUSWERTUNG.md` aktualisiert. Sie
liest alle erhaltenen alten und neuen ZIP-Ergebnisse, führt unvollständige
Versuche sowie historische 1:1-Doppelläufe getrennt auf und löscht keine
Rohdaten. `TESTBOT_AUSWERTUNG.bat`
erzeugt dieselbe Auswertung jederzeit erneut. Überlappende Ein- und
Dreijahreszeiträume werden nicht zu einer künstlichen Kapitalkurve addiert.

Angezeigt werden unter anderem:

- Netto-USDT-Gewinn/-Verlust
- Rendite
- Endkapital
- Tradezahl
- Profit Factor
- Winrate
- Max Drawdown
- Anteil der verfügbaren Kapitalzeit, in der Kapital eingesetzt war
- Anteil des Testfensters ganz ohne offene Position
- durchschnittliche und maximale Zahl gleichzeitig offener Positionen
- gesamte und zusätzliche Entry-Blöcke
- maximale gleichzeitig aktive Entry-Blöcke und maximal gebundenes Kapital
- Paarbeitrag im gemeinsamen Portfolio
- tatsächlicher Backtestzeitraum
- Candle-Integritätsstatus

## Was ein Backtest nicht beweist

Ein historischer OHLCV-Backtest rekonstruiert weder historische Orderbuch-Warteschlangen noch echte Netzwerklatenz oder Tick-für-Tick-Ausführung. Das 1m-Detail verbessert die Simulation, ersetzt diese Informationen aber nicht.

Deshalb bleibt der normale Backtest ein wichtiger, aber nicht allein ausreichender Research-Beweis. Robuste Kandidaten müssen zusätzlich gegen zeitliche Slices, Kostenstress, Walk-Forward/Blind-Evidenz und – wenn relevant – Replay-/Execution-Stress geprüft werden.

## V12-Research und aktive Kandidaten

Die V12-Optimizer/Family-League-Runs dienen der schnellen Kandidatensuche. Ein dort gefundener Gewinner ist **noch nicht automatisch die aktive Strategy**. Erst ein ausdrücklich promovierter Kandidat wird in die aktive Strategy-Datei übernommen und anschließend mit dem exakten lokalen Freqtrade-Backtest gegengeprüft.

Kein Backtestpfad darf Echtgeldorders senden.
