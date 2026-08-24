# Backtest in der Testbot-Oberfläche

## Maßgeblicher Grundsatz

Der UI-Backtest verwendet **keine separate Backtest-Strategie**. Für jeden Lauf wird die tatsächlich aktive Datei

`runtime/user_data/strategies/CompressionBreakout250.py`

neu gehasht und über den gesperrten Freqtrade-Backtestpfad geladen.

Auf dem Branch `agent/v12-17-ten-pair-research-ui` repräsentiert diese aktive
Strategy-Quelle den **V12.22-Paper-/Dry-run-Kandidaten** des Bots. Die eingefrorene
V8-Baseline unter
`research/baselines/V8/` bleibt davon getrennte Replay-/Audit-Evidenz.

## Auswahl

Im UI können getestet werden:

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

Die normale Oberfläche hat bewusst nur zwei Startaktionen:

- `Gewählten Coin testen`: ein ausgewählter Coin mit eigenem 250-USDT-Testwallet.
- `Alle 10 einzeln testen`: zehn automatische Läufe nacheinander, jeder Coin mit
  einem neuen eigenen 250-USDT-Testwallet.

Die zehn Ergebnisse bleiben getrennt und dürfen nicht als gemeinsames Konto
addiert werden. Der gemeinsame Portfolio-Lauf mit einem einzigen 250-USDT-Wallet
bleibt als interner Replay-/Audit-Pfad erhalten, ist aber kein normaler UI-Knopf.

`Alle 10 einzeln testen` ist ein dauerhaft gespeicherter Server-Batch. Nach
jedem Coin werden Batchplan und Zwischenresultat unter
`runtime/user_data/backtest_results/ui/_BATCHES/` aktualisiert. Ein Schließen
oder Neuladen der Backtest-Seite stoppt den Batch nicht. Nach einem Bot-Neustart
kann ein unvollständiger Batch fortgesetzt werden; bereits fertige identische
Zellen werden aus der erhaltenen Evidenz geladen und nicht neu berechnet.

Alle Signale bleiben **pair-lokal**. V12.22 injiziert kein BTC-Regime in andere
Pairs. BTC und ETH behalten ihre markierten Trend-Reclaims; die übrigen acht
Paare handeln den Broad-Core-Donchian-Pfad. Nur SOL verlangt bei diesem bereits
vorhandenen Einstieg zusätzlich `adx_4h >= 21`. Die 72-Stunden-Pairpause nach zwei
unprofitablen Trades und der +5-%-Stopboden nach mindestens +30 % bei
Champion-Trades bleiben erhalten. Ein zweiter oder dritter Block im selben
Trade ist nur für BTC, ETH, LINK und TRX bei einem neuen Signal, positivem Trade
und einem Kurs über allen früheren Entry-Fills erlaubt. SOL, XRP, BNB, DOGE,
LTC und BCH behalten normale erste Entries, aber keine Zusatzblöcke.
Verlust-Nachkauf bleibt gesperrt.

## Benötigte Daten

Für das ausgewählte Pair werden benötigt:

- 15m – Strategie-/Signal-Timeframe
- 1m – Detail-Timeframe für realistischere Intracandle-Simulation
- 1h – informatives Pair-Timeframe
- 4h – informatives Pair-Timeframe

Vor dem Lauf werden Daten aktualisiert und fehlende ältere Bereiche mit dem Freqtrade-Prepend-Pfad ergänzt.

Die Kerzen werden dauerhaft im lokalen, von Git ausgeschlossenen Botpfad

`runtime/user_data/data/binance/`

gespeichert. Ein späterer Lauf verwendet den vorhandenen Bestand weiter und
lädt nur fehlende ältere beziehungsweise neue Kerzen nach. Schlägt die
Integritätsprüfung wegen einer unterbrochenen, lückenhaften oder beschädigten
Datei fehl, wird ausschließlich der betroffene Coin-Datensatz neu aufgebaut.
Backtests, Paper-Datenbank und Strategy-Quelle werden dabei nicht gelöscht.

V12.22 verarbeitet Stop-Loss und Exit weiterhin auf jeder 1-Minuten-Detailkerze.
Nur die Prüfung eines zusätzlichen Entry-Blocks wird im Backtest auf die neue
15-Minuten-Strategiekerze begrenzt, weil sich das dafür verwendete
`enter_long`-Signal dazwischen nicht ändern kann. Zusätzlich entfallen defensive
Trade-Kopien ausschließlich für drei getestete, schreibgeschützte Callbacks.
Der Paper-/Dry-run-Ablauf bleibt davon unberührt.

Der Lauf bricht fail-closed ab, wenn Daten fehlen, Zeitstempel nicht monoton sind, Duplikate/Lücken vorhanden sind oder das benötigte Fenster nicht vollständig abgedeckt ist.

## Vom Einzeltest zur pair-spezifischen Verbesserung

Das Ziel der Einzeltests ist, jeden der zehn Coins unabhängig zu beurteilen und
später nur dort eigene Parameter zu verwenden, wo belastbare Daten eine
Verbesserung zeigen. Der normale UI-Backtest ist dafür die Messung des **aktuell
laufenden Bots**; er ist absichtlich kein selbstverändernder Optimierer.

Der verbindliche Verbesserungszyklus lautet:

1. Aktuelle Strategy für einen Coin über einen ausgewählten, noch nicht
   identisch ausgeführten Zeitraum von ein, zwei oder drei Jahren messen.
2. Tradezahl, Verlustcluster, Profit Factor, Drawdown, Kapitalnutzung,
   Entry-/Exit-Familien und Gebührenempfindlichkeit auswerten.
3. Genau eine begründete pair-spezifische Änderung als neue, im Trial Ledger
   registrierte Strategy-Version erstellen. Die aktive Datei wird nicht während
   eines laufenden Bots verändert.
4. Entwicklung, Validierung und unangesehenen Holdout beziehungsweise
   Walk-Forward trennen; Kostenstress und Datei-/Kerzen-Audit ausführen.
5. Nur einen nach diesen Prüfungen besseren Kandidaten ausdrücklich in den
   Paperbot übernehmen.
6. Danach den gemeinsamen Zehn-Paare-Systemtest ausführen. Dort konkurrieren die
   zehn verbesserten Pair-Routen um dasselbe reale Modell mit 250 USDT und
   höchstens drei 80-USDT-Blöcken.

Damit kann beispielsweise LINK andere Parameter als TRX erhalten, ohne aus zehn
Einzelwallets fälschlich ein 2.500-USDT-Portfolio zu bilden. Ein schöner
In-Sample-Lauf allein gilt nicht als „optimal“ und ändert den Bot niemals
automatisch.

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
Beschreibung umgehen die Sperre nicht. Im Zehner-Batch werden bestehende Zellen
als „Vorhanden“ angezeigt und ohne erneute Simulation in die Matrix übernommen.

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

Zusätzlich entstehen unter `_PAIR_HISTORIEN/` je Coin und Zeitraum eine JSON-
und Markdown-Akte. Sie enthält alle erhaltenen Läufe, den letzten materiell
anderen Vorgänger, die Änderungen bei Gewinn, Tradezahl, Profit Factor,
Drawdown und Kapitalnutzung sowie die verbindliche Regel gegen 1:1-Doppelläufe.
Jeder einzelne Ergebnisordner erhält dieselbe Historie und getrennte Zeitmessung
für Datenpflege, Simulation und Auswertung.

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
