# Codex-Auftrag: Bot bis zur Live-Reife weiterbauen und einen echten historischen Live-Replay integrieren

## Zweck dieser Datei

Diese Datei ist der Arbeitsauftrag für die nächste große Codex-Phase im Repository `boomarank2-commits/ai-trading-agent`.

Arbeite nicht nur die unten genannten Punkte mechanisch ab. Prüfe den aktuellen Repository-Zustand zuerst selbst vollständig, verifiziere frühere Annahmen erneut und korrigiere bestehende Implementierungen, falls sie technisch nicht belastbar sind. Das Ziel ist kein schön aussehender Backtest und keine möglichst hohe historische Rendite, sondern ein reproduzierbares, sicheres und technisch ehrliches System, das im Paper-/Forward-Betrieb 24/7 laufen kann und dessen heutiges Verhalten zusätzlich über historische Binance-Daten möglichst realitätsnah simuliert werden kann.

Die öffentliche DaviddTech-/AI-Trader-MCP-Architektur ist als Inspiration zu verstehen, nicht als Beweis einer profitablen Strategie. Der öffentliche DaviddTech-Code ist ein Research-/Agenten-Layer und kein vollständiger Exchange-Bot. Die fehlende lokale Runtime wurde in diesem Repository bereits mit Freqtrade, einer Registry, Hash-/Promotion-Gates und einem sicheren Paper-/Recovery-Pfad ergänzt. Diese gute Trennung darf nicht leichtfertig zerstört werden.

---

# 1. Ausgangslage, die du zuerst selbst verifizieren musst

Der aktuelle Stand enthält unter anderem:

- Freqtrade `2026.7` als lokale deterministische Runtime.
- Binance Spot, derzeit BTC/USDT, ETH/USDT und SOL/USDT.
- 15-Minuten-Haupttimeframe.
- Dry-run mit 250 virtuellen USDT.
- maximal drei Positionen mit bis zu 80 USDT pro Position und 240 USDT Gesamtengagement.
- Long-only, Spot, 1x.
- kein Margin, Futures, Short, DCA oder Martingale.
- Entry-Kill-Switch.
- Tagesverlust-Sperre für neue Entries.
- Registry-/Lifecycle-Konzept mit RESEARCH -> VALIDATED -> HOLDOUT_PASSED -> SHADOW -> PAPER -> CANARY -> PRODUCTION.
- Hashbindung von Strategie/Config/Dependencies und manuelle Freigabegates.
- Lookahead- und Recursive-Analyse.
- getrennten pausierten Live-Recovery-Pfad ohne freigegebene Echtgeld-Entries.
- einen 24/7-Dry-run-Testpfad über `STARTBOT.bat`.

Die bisher untersuchten Strategien waren negativ und wurden korrekt verworfen. Das ist kein Fehler, sondern gewünschtes Verhalten. Ein System, das schlechte Strategien ablehnt, ist wertvoller als eines, das Parameter so lange verändert, bis ein schöner Backtest erscheint.

Prüfe alle oben genannten Punkte direkt im aktuellen Code. Verlasse dich nicht nur auf README-Dateien.

---

# 2. Oberstes Ziel

Es sollen zwei eng miteinander verwandte, aber klar getrennte Betriebsarten existieren:

## A. Echter 24/7-Paper-/Forward-Betrieb

Der Bot erhält fortlaufend aktuelle Binance-Marktdaten, verarbeitet nur Informationen, die zu diesem Zeitpunkt tatsächlich verfügbar sind, trifft seine Entscheidungen mit derselben Runtime-Logik, speichert Zustand dauerhaft und kann nach Neustarts sauber fortsetzen.

Dieser Modus ist die Referenz für das reale Verhalten.

## B. Historischer Live-Replay / Zeitmaschinen-Modus

Historische Binance-Daten der vergangenen etwa drei bis vier Jahre werden chronologisch abgespielt, als würden sie gerade live eintreffen.

Der Bot darf zu einem simulierten Zeitpunkt `t` ausschließlich Informationen sehen, die bis `t` tatsächlich bekannt waren. Der Replay-Modus soll nicht nur eine fertige Strategieformel über einen DataFrame rechnen, sondern möglichst dieselben Entscheidungs-, Risiko-, Portfolio-, Persistenz- und Orderpfade verwenden wie der 24/7-Betrieb.

Die Kernfrage des Replay-Modus lautet:

> Wenn exakt die heute eingefrorene Bot-Version damals schon gelaufen wäre und immer nur die jeweils damals verfügbaren Daten gesehen hätte: Welche Entscheidungen hätte sie getroffen, welche Trades wären simuliert entstanden, wann hätte sie Entries gesperrt, Strategien hoch- oder heruntergestuft und wie hätte sich das Portfolio entwickelt?

Das ist etwas anderes als ein normaler Freqtrade-Backtest.

---

# 3. Sehr wichtige Unterscheidung: klassischer Backtest vs. historischer Live-Replay

Baue **beide** Varianten.

## 3.1 Klassischer Strategie-Backtest

Zweck:

- schnelle Strategieprüfung,
- Backtest-Matrix,
- Parameter-/Robustheitsvergleich,
- Lookahead-/Recursive-Diagnostik,
- Jahres-/Monats-/Pair-Auswertung,
- schneller Ausschluss schlechter Strategien.

Freqtrade darf dafür weiterhin verwendet werden.

Bestehende Backtest-Skripte nicht unnötig ersetzen, sondern verbessern und sauber in einen eigenen Bereich integrieren.

## 3.2 Historischer Live-Replay

Der Replay muss deutlich näher am tatsächlichen 24/7-Prozess liegen.

Anforderungen:

1. Eine monotone Simulationsuhr steuert den gesamten Prozess.
2. Daten werden strikt zeitlich sortiert eingespeist.
3. Zu Zeitpunkt `t` sind nur vollständig abgeschlossene Kerzen bis `t` sichtbar.
4. Kein Modul darf Zugriff auf spätere Kerzen erhalten.
5. Die aktuelle 15m-Kerze darf erst nach ihrem Close für 15m-Signale genutzt werden.
6. Ein Entry darf nicht rückwirkend zum perfekten Preis derselben Signal-Kerze ausgeführt werden.
7. Der gleiche Risk-Manager bzw. dieselben Risk-Regeln wie im Paper-/Live-Pfad müssen gelten.
8. Portfolio-Limits, offene Positionen, Tagesverlustsperren, Kill-Switch-Zustand, Cooldowns und andere zustandsabhängige Regeln müssen historisch mitgeführt werden.
9. Neustarts müssen simulierbar sein. Ein Replay muss an einem gespeicherten Checkpoint fortgesetzt werden können und danach dasselbe Ergebnis liefern.
10. Wiederholte Ausführung derselben Daten mit demselben Commit, denselben Konfigurationen und demselben Seed muss deterministisch zum gleichen Ergebnis führen.

Wenn Freqtrade intern nicht geeignet ist, um den vollständigen Runtime-Prozess auf diese Weise wiederzuverwenden, baue einen separaten Replay-Adapter, aber dupliziere die eigentliche Trading-/Risk-Logik nicht. Das Ziel ist eine gemeinsame Kernlogik mit austauschbaren Adaptern für Uhr, Marktdaten und Execution.

Beispiel:

```text
                   gemeinsame Kernlogik
                           |
        --------------------------------------------
        |                    |                     |
   Live/Paper Adapter   Replay Adapter      klassischer Backtest
   echte Uhr            Simulationsuhr      Freqtrade Engine
   Binance Stream       historische Daten   historischer DataFrame
   Dry-run Orders       simulierte Orders   Backtest-Fills
```

---

# 4. Historische Binance-Daten

Baue einen separaten, einfach bedienbaren Datenbereich für den Replay/Backtest.

## 4.1 Zielzeitraum

Standardmäßig sollen mindestens drei Jahre und möglichst vier Jahre geladen werden.

Am aktuellen Projektzeitpunkt wäre ein sinnvoller Zielbereich ungefähr:

- vier Jahre: etwa August 2022 bis zum letzten vollständig verfügbaren Zeitpunkt,
- alternativ drei Jahre, wenn ein bestimmter Datenbereich nicht zuverlässig verfügbar ist.

Der Downloader soll nicht blind davon ausgehen, dass jede Datei vorhanden ist. Er muss die tatsächliche Datenabdeckung pro Pair und Timeframe prüfen und dokumentieren.

## 4.2 Quelle

Bevorzuge offizielle öffentliche Binance-Marktdaten bzw. offizielle Freqtrade-Downloadmechanismen auf Basis der Binance-API.

Keine privaten API-Keys für historische Marktdaten.

Wenn sinnvoll, unterstütze die offiziellen Binance-Public-Data-Archive zusätzlich zum Freqtrade-Downloader, insbesondere für große Zeiträume.

## 4.3 Timeframes

Für das aktuelle System:

- 15m als Haupttimeframe für die Strategie,
- zusätzlich **1m Detaildaten** für eine genauere Intracandle-/Fill-Simulation.

Freqtrade unterstützt für Backtests einen kleineren `--timeframe-detail`. Nutze dies im verbesserten klassischen Backtest.

Der historische Live-Replay darf die 1m-Daten auch selbst zur realistischeren Fill-/Stop-/Exit-Auswertung nutzen.

Falls 1m für einen Teilbereich fehlt, darf nicht stillschweigend auf optimistische 15m-Annahmen zurückgefallen werden. Entweder konservativ behandeln oder den Run als eingeschränkt kennzeichnen.

## 4.4 Datenintegrität

Für jeden Datenbestand soll ein Manifest existieren mit mindestens:

- Quelle,
- Exchange,
- Symbol,
- Trading-Mode,
- Timeframe,
- Startzeit,
- Endzeit,
- Anzahl Kerzen,
- erkannte Lücken,
- Downloadzeit,
- Dateihashes/Checksums,
- Parser-/Importer-Version.

Prüfe doppelte Kerzen, fehlende Intervalle, unsortierte Zeitstempel und Zeitzonenprobleme.

Alle internen Zeiten UTC.

Beachte beim direkten Import offizieller Binance-Public-Data-Dateien Änderungen des Timestamp-Formats. Parser dürfen nicht implizit Millisekunden annehmen, wenn Quelldaten inzwischen Mikrosekunden enthalten können.

---

# 5. Ehrlichkeit des historischen Tests: kein Future Leakage

Das ist nicht verhandelbar.

## 5.1 Daten-Leakage

Kein Modul darf im Replay zukünftige OHLCV-Werte, spätere Kennzahlen, spätere Portfolioergebnisse oder spätere Regimeklassifikationen sehen.

Alle Features müssen kausal berechnet werden.

Verboten bzw. kritisch zu prüfen:

- negative Shifts,
- zentrierte Rolling-Windows,
- globale Mittelwerte über den gesamten Datensatz,
- falsch gemergte höhere Timeframes,
- aktuelle Dynamic-Pairlist-Informationen als Ersatz für historische Pairlisten,
- Indikatoren, die erst durch spätere Daten stabil werden,
- Optimierung auf dem finalen Holdout.

Lookahead- und Recursive-Analyse bleiben Pflicht.

## 5.2 LLM-/Codex-Leakage

Ein extrem wichtiger Punkt:

Ein heutiges LLM besitzt Wissen und Trainingskontext, der zeitlich nach Teilen des historischen Replay-Zeitraums liegt. Deshalb darf im strikten historischen Live-Replay **kein LLM während des simulierten Jahres 2022/2023/2024 spontan neue Strategien aufgrund angeblich damaliger Marktinformationen erzeugen und dieses Ergebnis anschließend als echten Out-of-Sample-Beweis verkaufen**.

Für den ehrlichen Replay:

- Strategiecode,
- Managerlogik,
- Rankingformel,
- Promotion-/Demotion-Regeln,
- Risk-Regeln

werden vor Start des Replay-Runs eingefroren und gehasht.

Während des Replay darf sich das System nur innerhalb dieser vorher definierten Regeln anpassen.

Wenn später ein experimenteller „AI Research Replay“ gebaut wird, muss er separat gekennzeichnet sein und darf niemals mit dem strikten historischen Live-Replay verwechselt werden.

---

# 6. Research-/Portfolio-Manager vervollständigen

Prüfe, wie weit diese Architektur im aktuellen Repository bereits umgesetzt ist. Ergänze fehlende Teile sauber.

Das gewünschte Prinzip ist nicht „ein einzelner Bot schreibt sich nach jedem Verlust um“, sondern:

```text
Research -> Kandidaten -> Validierung -> Shadow/Paper -> Ranking ->
Portfolioauswahl -> laufende Performancebewertung -> Promotion/Demotion
```

Falls noch nicht vorhanden, implementiere einen nachvollziehbaren Strategy-League-/Champion-Challenger-Ansatz.

## 6.1 Strategy League

Mehrere Strategien/Kandidaten können gleichzeitig virtuell beobachtet werden.

Jede Strategie erhält getrennte Kennzahlen:

- Tradezahl,
- Nettoergebnis,
- Profit Factor,
- Winrate,
- Expectancy,
- durchschnittlicher Gewinn/Verlust,
- Max Drawdown,
- längste Verlustserie,
- Recovery Time,
- Rolling Performance,
- Performance pro Pair,
- Performance pro Marktregime,
- Kosten-/Slippage-Sensitivität.

## 6.2 Rolling Evaluation

Nicht nur Gesamtperformance seit Start betrachten.

Mindestens Fenster für z. B.:

- letzte 20 Trades,
- letzte 50 Trades,
- letzte 100 Trades,
- 7 Tage,
- 30 Tage,
- 90 Tage.

Aber: Kleine Samples nicht überbewerten. Konfidenz/Unsicherheit sichtbar machen.

## 6.3 Promotion und Demotion

Promotion niemals aufgrund eines einzigen guten Backtests.

Der aktuelle Lifecycle mit Validation/Holdout/Shadow/Paper soll erhalten und technisch durchgesetzt werden.

Eine Strategie, die im Forward-Betrieb deutlich schlechter wird, soll abgestuft oder quarantänisiert werden können, ohne dass ihr historischer Datensatz gelöscht oder überschrieben wird.

Beispiel:

```text
PRODUCTION -> REDUCED/QUARANTINE -> RESEARCH
```

Falls die vorhandene Registry andere Namen nutzt, passe das Konzept sauber an statt parallel ein zweites widersprüchliches Lifecycle-System einzuführen.

## 6.4 Regime-Erkennung

Optional, aber sinnvoll, sofern kausal und robust implementiert:

- Trend,
- Seitwärts/Mean-Reversion,
- hohe Volatilität,
- niedrige Volatilität.

Regime dürfen nur aus damals verfügbaren Daten bestimmt werden.

Keine exotische Komplexität nur um Backtests zu verbessern.

---

# 7. Live-/Paper-Reife vor echter Freigabe

Der Bot soll technisch so vollständig werden, dass man nach erfolgreicher Validierung sagen kann: „Die Architektur wäre prinzipiell live-fähig.“

**Das bedeutet ausdrücklich nicht, Echtgeld-Entries jetzt freizuschalten.**

Vervollständige bzw. prüfe:

## 7.1 Marktdaten

- robuste Echtzeitversorgung,
- bevorzugt WebSocket für aktuelle Marktdaten, wenn es sinnvoll und stabil ist,
- REST-Fallback,
- Reconnect mit Backoff,
- Erkennung veralteter Daten,
- Erkennung fehlender Kerzen,
- keine Entscheidung auf stale data.

## 7.2 Execution-/Order-State

- idempotente Orderbehandlung,
- keine Doppelorder nach Restart,
- sauberer Zustand `requested/open/partially_filled/filled/cancelled/rejected`, soweit Runtime/Exchange dies unterstützt,
- Reconciliation nach Neustart,
- Schutz vor widersprüchlichem lokalen/Exchange-Zustand,
- fail closed bei unbekanntem Zustand.

Der Research-Agent erhält weiterhin keinen direkten Exchange-Key und keine freie Orderfunktion.

## 7.3 Persistenz und Restart

Nach Prozessabbruch oder Windows-Neustart muss der Paper-Bot sauber erkennen:

- aktuelle offene Trades,
- Tages-PnL,
- Risk-Limits,
- letzte verarbeitete Kerze,
- aktive Strategieversion,
- laufende Promotions-/Evaluationstates.

Keine doppelte Verarbeitung derselben Candle nach Neustart.

## 7.4 Health und Watchdog

Mindestens:

- Heartbeat,
- Datenalter,
- letzter erfolgreicher Candle-Cycle,
- offene Trades,
- DB-Zustand,
- Exchange-/Data-Verbindung,
- Prozessstatus,
- Risk-Lock-Status,
- Restart-Zähler.

Fehler sollen sichtbar protokolliert werden und nicht still weiterlaufen.

## 7.5 Kill-Switch

Der vorhandene Entry-Kill-Switch bleibt erhalten.

Zusätzlich prüfen, ob separate Modi sinnvoll sind:

- `STOP_NEW_ENTRIES`,
- `PAUSE_MANAGER`,
- `EMERGENCY_MANAGE_ONLY`.

Keine automatische Panik-Schließung aller Positionen bei jedem technischen Fehler. Das Verhalten muss bewusst und dokumentiert sein.

---

# 8. Realistische Kosten- und Fill-Simulation

Der aktuelle Backtest nutzt konservativ `0.002` pro Seite als Proxy für Gebühr plus Slippage. Behalte diese konservative Baseline zunächst bei, prüfe aber die Logik und mache sie explizit konfigurierbar.

Mindestens folgende Kosten-Szenarien sollen vergleichbar sein:

- günstiges Szenario,
- Baseline,
- Stress-Szenario.

Nicht nur einen einzigen Kostenwert optimieren.

Der Replay-/Backtest-Bericht muss immer klar angeben:

- Fee pro Seite,
- Slippageannahme,
- Roundtrip-Kosten,
- Orderarten,
- Fill-Modell.

## Intracandle

Da die Strategie auf 15m läuft, nutze 1m Detaildaten, damit Stops/Exits und freie Trade-Slots realistischer simuliert werden.

Wenn innerhalb einer 1m-Kerze sowohl Stop als auch Ziel theoretisch berührt werden und die Reihenfolge unbekannt ist, verwende keine systematisch optimistische Annahme. Dokumentiere die gewählte konservative Regel.

Limitorders dürfen nicht automatisch als gefüllt gelten, wenn der Markt sie nicht plausibel erreicht hat.

Marketorders erhalten Slippage.

Gaps müssen berücksichtigt werden.

---

# 9. Backtest-/Replay-Struktur im Repository

Baue einen klar getrennten Bereich, z. B.:

```text
historical/
  data/
  manifests/
  replay/
  reports/
  scripts/
```

oder eine technisch bessere Struktur, falls sie sauberer zum bestehenden Projekt passt.

Wichtig:

- historische Replay-Datenbank niemals mit dem laufenden Paper-Bot teilen,
- eigene Run-IDs,
- eigene Logs,
- eigene Trade-Historie,
- keine Seiteneffekte auf `STARTBOT.bat`,
- keine Live-Credentials,
- große Marktdaten und Resultate bleiben aus Git ausgeschlossen,
- kleine reproduzierbare Test-Fixtures dürfen versioniert werden.

---

# 10. Benutzerfreundliche Windows-Starts

Der Nutzer soll das System ohne lange Kommandozeilen bedienen können.

Erhalte `STARTBOT.bat` für den normalen 24/7-Test.

Ergänze sinnvoll benannte Startdateien, beispielsweise:

```text
HISTORISCHE_DATEN_LADEN.bat
HISTORISCHER_BACKTEST.bat
HISTORISCHER_LIVE_REPLAY.bat
HISTORISCHE_AUSWERTUNG.bat
```

Namen dürfen anders gewählt werden, wenn sie klarer sind.

Beim Start des historischen Bereichs soll der Nutzer auswählen können:

- 1 Jahr,
- 3 Jahre,
- 4 Jahre,
- benutzerdefinierter Zeitraum.

Default: 4 Jahre, sofern Datenabdeckung vollständig genug ist.

Der Nutzer soll sehen:

- welche Daten vorhanden sind,
- welche fehlen,
- welches Pair/Timeframe verwendet wird,
- welche Bot-/Strategieversion geprüft wird,
- welcher Zeitraum simuliert wird,
- welcher Modus läuft: klassischer Backtest oder echter Live-Replay.

---

# 11. Ergebnisberichte

Jeder Replay-/Backtest-Run bekommt eine unveränderliche Run-ID und ein Manifest.

Mindestens speichern:

```text
run_id
start/end UTC
Git commit SHA
strategy name/version/hash
config hash
risk-policy hash
data-manifest hashes
Freqtrade version
Python version
seed
fee/slippage model
replay/backtest mode
```

Ergebnisse mindestens:

- Startkapital,
- Endkapital,
- Netto-PnL,
- Rendite,
- Profit Factor,
- Max Drawdown,
- Winrate,
- Expectancy,
- Tradeanzahl,
- durchschnittliche Haltedauer,
- längste Verlustserie,
- Recovery Time,
- Monats-/Jahresergebnisse,
- pro Pair,
- pro Strategie,
- pro Regime, falls Regime genutzt werden,
- Kosten vor/nach Fees/Slippage,
- abgelehnte Entries und Grund,
- Risk-Lock-Ereignisse,
- Restarts/Fehlerereignisse.

Erzeuge zusätzlich maschinenlesbar:

- `manifest.json`,
- `metrics.json`,
- `trades.csv` oder Parquet,
- `equity.csv` oder Parquet,
- `decisions.jsonl`,
- `events.jsonl`,
- `errors.jsonl`.

Dateinamen können an bestehende Konventionen angepasst werden.

---

# 12. Retrospektiver Replay ist nicht automatisch Out-of-Sample

Kennzeichne Ergebnisse korrekt.

Wenn eine Strategie heute entwickelt wurde und anschließend auf 2022-2026 zurückgerechnet wird, ist das ein **retrospektiver Stresstest**, aber kein echter Beweis, dass man 2022 die Strategie so ausgewählt hätte.

Deshalb zwei Berichtsklassen:

## A. Retrospektiver Full-System-Replay

Heute eingefrorene Botversion wird rückwärts über historische Daten simuliert.

Nutzen:

- Stabilität,
- Fehlersuche,
- verschiedene Marktphasen,
- Risk-Verhalten,
- mögliche historische Robustheit.

Nicht als vollständiger Out-of-Sample-Nachweis bezeichnen.

## B. Strikter Walk-Forward/Holdout-Test

Für neue Strategien:

- Entwicklung nur auf frühem Datenfenster,
- Strategie einfrieren,
- danach Walk-Forward,
- finales Holdout erst am Ende öffnen,
- keine nachträgliche Optimierung auf Holdout.

Bei vier Jahren Daten ist beispielsweise möglich:

```text
24 Monate Research/Development
12 Monate Walk-Forward/Validation
12 Monate finaler unangetasteter Holdout
```

Das ist nur ein Startpunkt. Prüfe statistisch sinnvolle Fenster und dokumentiere die Entscheidung.

---

# 13. Robustheit statt „Backtest gewinnen“

Codex darf NICHT die Aufgabe missverstehen als:

> „Optimiere so lange, bis die letzten vier Jahre profitabel aussehen.“

Das wäre Overfitting.

Stattdessen:

1. Hypothese festlegen.
2. Version einfrieren.
3. Testen.
4. Diagnose erstellen.
5. Bei schlechter Hypothese verwerfen.
6. Bei neuer Idee neue Version erstellen.
7. Holdout nicht mehrfach zur Optimierung missbrauchen.

Die bestehenden Gates wie Profit Factor, Drawdown, Mindesttradezahl und positive Slices dürfen überprüft und bei guter statistischer Begründung verbessert werden, aber niemals stillschweigend gelockert werden, nur damit ein Kandidat durchkommt.

---

# 14. Zusätzliche Stress- und Fehlerreplays

Ein Bot, der nur bei perfekten Daten läuft, ist nicht live-reif.

Baue reproduzierbare Fault-Injection-Tests für mindestens:

- fehlende einzelne Candle,
- verspätete Candle,
- doppelte Candle,
- unsortierte Daten,
- temporärer REST-/WebSocket-Fehler,
- Rate-Limit/Timeout,
- Prozessrestart bei offener Position,
- Restart direkt nach Entry-Signal,
- Datenbank temporär nicht verfügbar/gelockt,
- beschädigter Checkpoint,
- stale market data,
- Kill-Switch während offener Position.

Erwartung: fail closed für neue Entries, aber vorhandene Positionen konsistent verwalten, soweit sicher möglich.

---

# 15. Testanforderungen

Füge Tests hinzu, nicht nur Code.

## Unit Tests

- Zeit-/Candle-Grenzen,
- kausale Featureberechnung,
- Risk-Limits,
- Rolling Metrics,
- Promotion/Demotion,
- Slippage/Fee-Modell,
- Datenlückenerkennung,
- Checkpointing.

## Integration Tests

- kompletter kleiner Replay auf versioniertem Mini-Dataset,
- Restart mitten im Replay,
- wiederholter Run liefert identischen Output,
- Paper-/Replay-Entscheidungsparität auf demselben Candle-Stream,
- Registry-/Lifecycle-Integration.

## Golden Test

Lege einen kleinen unveränderlichen historischen Testdatensatz an, dessen erwartete Events/Trades/Hashwerte bekannt sind.

Änderungen am Kernverhalten müssen diesen Golden-Test entweder bestehen oder bewusst mit dokumentierter Begründung aktualisieren.

## Existing Tests

Alle vorhandenen pytest-/ruff-/runtime-/registry-Tests müssen weiterhin bestehen.

---

# 16. Parität zwischen Live/Paper und Replay

Das ist eines der wichtigsten Abnahmekriterien.

Baue eine Möglichkeit, einen gespeicherten echten Paper-Market-Data-Stream später erneut durch den Replay-Adapter zu schicken.

Bei identischem Input sollen Signalentscheidungen und Risk-Entscheidungen übereinstimmen.

Abweichungen müssen erklärbar sein, beispielsweise:

- echter Fillpreis vs. simulierter Fillpreis,
- Netzwerklatenz,
- Orderstatus der Börse.

Aber die eigentliche Strategieentscheidung auf derselben abgeschlossenen Candle darf nicht zufällig anders sein.

---

# 17. Sicherheitsgrenzen beibehalten

Folgende Grundsätze nicht abschwächen:

- keine Secrets in Git,
- keine Secrets in Logs,
- kein LLM mit direktem Exchange-Key,
- keine Withdrawal-Berechtigung,
- kein Margin/Futures,
- keine automatische Live-Freigabe aufgrund eines Backtests,
- exakte Strategie-/Config-/Dependency-Hashes,
- manuelle Freigabe vor Canary/Production,
- Live-Start bleibt bis zur vollständigen Validierung gesperrt bzw. paused.

„Theoretisch live-ready“ bedeutet:

- Executionpfad ist technisch vorhanden,
- Reconciliation funktioniert,
- Risk-Gates funktionieren,
- Recovery funktioniert,
- Observability funktioniert,
- Replay/Backtest/Forward-Tests sind bestanden,

aber Echtgeld-Entries werden nicht automatisch aktiviert.

---

# 18. Konkrete Arbeitsreihenfolge

## Phase 0 – unabhängiger Re-Audit

1. komplettes Repository lesen,
2. aktuelle Architektur dokumentieren,
3. alle vorhandenen Tests ausführen,
4. bekannte Annahmen gegen aktuellen Code verifizieren,
5. offizielle aktuelle Freqtrade- und Binance-Dokumentation prüfen,
6. Lückenliste erstellen,
7. erst danach Code ändern.

Keine Annahme aus dieser Datei ungeprüft übernehmen, wenn der aktuelle Code bereits eine bessere Lösung enthält.

## Phase 1 – 24/7-Paper-/Live-Readiness vervollständigen

- Datenversorgung,
- Persistenz,
- Reconciliation,
- Health/Watchdog,
- Strategy-/Portfolio-Manager,
- Rolling Evaluation,
- Promotion/Demotion,
- Risk-Gates,
- Restart-Sicherheit.

Live-Entries bleiben deaktiviert.

## Phase 2 – historische Datenpipeline

- 3-4 Jahre Binance-Daten,
- 15m + 1m,
- Manifeste,
- Hashes,
- Lückenprüfung,
- reproduzierbare lokale Speicherung.

## Phase 3 – klassischen Backtest verbessern

- 15m Strategie,
- 1m timeframe-detail,
- Costs,
- Breakdown,
- exportierte Signals/Trades,
- Lookahead,
- Recursive,
- Jahres-/Pair-/Robustheitsreports.

## Phase 4 – echter historischer Live-Replay

- Simulationsuhr,
- point-in-time Datensicht,
- gemeinsame Kernlogik,
- persistenter Zustand,
- Ordersimulation,
- Checkpoints,
- Restart,
- Strategy League/Manager,
- Risk-Events.

## Phase 5 – Paritäts- und Fault-Tests

- Golden Dataset,
- Paper-vs-Replay-Parität,
- Fault Injection,
- deterministische Wiederholung.

## Phase 6 – große historische Auswertung

Erst wenn die Engine selbst verifiziert ist:

- 3-Jahres-Run,
- 4-Jahres-Run,
- retrospektiver Full-System-Replay,
- Walk-Forward/Holdout wo methodisch möglich,
- Kostenstress,
- Monats-/Jahres-/Regimeanalyse.

## Phase 7 – echter Forward-Test

Danach weiter 24/7 mit virtuellem Geld auf echten neuen Binance-Daten.

Historie ersetzt diesen Forward-Test nicht.

## Phase 8 – Live-Readiness-Bericht

Noch keine automatische Echtgeldfreigabe.

Erzeuge einen expliziten Bericht:

```text
READY / NOT READY
```

mit allen noch offenen Punkten.

---

# 19. Abnahmekriterien

Die Phase gilt erst als abgeschlossen, wenn mindestens Folgendes erfüllt ist:

- vollständige Test-Suite grün,
- Ruff/Lint grün,
- kein Secret in Git,
- Replays sind deterministisch,
- Datenmanifest vollständig,
- keine erkannte Future-Leakage,
- Lookahead-/Recursive-Prüfungen dokumentiert,
- Replay verarbeitet Daten streng point-in-time,
- Replay und Paper teilen möglichst viel Kernlogik,
- 1m-Detaildaten werden für realistischere 15m-Fills verwendet,
- Restart aus Checkpoint reproduziert denselben Endzustand,
- Risk-Limits werden im Replay genauso erzwungen,
- Fault-Injection führt nicht zu unkontrollierten neuen Entries,
- Reports enthalten Commit-/Config-/Strategy-/Data-Hashes,
- historische Ergebnisse werden nicht als Gewinnversprechen dargestellt,
- negative Strategien werden weiterhin verworfen,
- kein Codepfad schaltet Echtgeld allein aufgrund guter Historie frei.

---

# 20. Was du am Ende liefern musst

1. den vollständig weitergebauten Code,
2. alle neuen Tests,
3. Windows-Startskripte für Daten/Backtest/Replay,
4. aktualisierte Dokumentation,
5. einen Beispiel-Replay auf einem kleinen Testzeitraum,
6. danach einen reproduzierbaren großen historischen Run, soweit lokal praktikabel,
7. einen Abschlussbericht `CODEX_COMPLETION_REPORT_DE.md` mit:

   - was vorher vorhanden war,
   - welche Schwächen gefunden wurden,
   - was geändert wurde,
   - welche Annahmen korrigiert wurden,
   - welche Tests liefen,
   - welche historischen Daten verwendet wurden,
   - welche Ergebnisse der klassische Backtest zeigte,
   - welche Ergebnisse der Full-System-Replay zeigte,
   - wo Backtest und Replay voneinander abweichen und warum,
   - welche Fault-Tests bestanden wurden,
   - welche Risiken offen bleiben,
   - ob der Bot technisch als `READY FOR EXTENDED PAPER TEST` gilt,
   - ob er ausdrücklich noch `NOT READY FOR REAL MONEY` ist.

---

# 21. Arbeitsweise für Codex

- Nicht nach der Planung aufhören: implementieren, testen, korrigieren.
- Bestehende gute Sicherheitsmechanismen erhalten.
- Keine großen Umbauten ohne vorher zu verstehen, was bereits funktioniert.
- Kein „quick fix“, der nur einen Test grün macht.
- Keine künstlichen Backtest-Gewinne.
- Keine versteckten Parameteränderungen nach Einsicht in den finalen Holdout.
- Kleine nachvollziehbare Commits.
- Nach jeder größeren Phase Tests ausführen.
- Dokumentation gleichzeitig mit Code aktualisieren.
- Bei einer falschen Annahme diese ausdrücklich korrigieren.
- Wenn eine Idee nicht funktioniert, Ergebnis dokumentieren und verwerfen, statt sie schönzurechnen.

Der wichtigste Maßstab ist nicht historische Maximalrendite, sondern:

> **Würde ich diesem exakt reproduzierbaren System zutrauen, monatelang unbeaufsichtigt mit virtuellem Geld zu laufen, ohne Daten zu cheaten, ohne Zustandsverlust und ohne seine eigenen Risikogrenzen zu umgehen?**

Erst wenn diese Frage technisch mit Ja beantwortet werden kann, ist der nächste Schritt Richtung Canary überhaupt sinnvoll.

---

# 19. Verbindlicher Projektstand nach Backtest-Audit vom 15.08.2026

Dieser Abschnitt ist eine **verbindliche Übergabe** für jeden nachfolgenden Codex-/Agentenlauf. Er dokumentiert, welche Änderungen seit dem ursprünglichen Auftrag tatsächlich umgesetzt und getestet wurden, welche Hypothesen verworfen wurden und welche Grenzen **nicht** wieder aufgeweicht werden dürfen.

## 19.1 Sicherheits- und Architekturentscheidungen, die nicht zurückgebaut werden dürfen

- Der normale Testbot bleibt Binance **Spot, long-only, dry-run/Paper**. Keine automatische Echtgeldfreigabe.
- Startkapital aktuell 250 USDT, maximal 80 USDT je Position, maximal drei Positionen und maximal 240 USDT Gesamtexposition.
- Der sichtbare STARTBOT-Prozess ist eine Sicherheitsgrenze. Das Windows-Job-Object mit `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` muss erhalten bleiben: stirbt der Supervisor bzw. wird das überwachte Testbot-UI geschlossen, darf kein versteckter Freqtrade-Prozess weiterlaufen.
- Der Backtest verwendet **keine zweite Strategie**. Der exakte aktuell getestete `CompressionBreakout250.py`-Quelltext wird pro Lauf gehasht und über `runtime/locked_backtest_freqtrade.py` geladen.
- Große OHLCV-Daten, Backtest-Resultate, Logs, SQLite-Datenbanken und Credentials bleiben aus Git.
- Keine Strategie wird allein wegen eines positiven Full-History-Backtests promoted. Walk-Forward/Holdout und anschließender Paper-Forward-Test bleiben Pflicht.

## 19.2 Relevante Repository-Historie

Die folgenden Änderungen erklären den aktuellen Aufbau. Nicht parallel neu erfinden, sondern auf ihnen aufbauen:

- PR #2: Windows-Lifetime-Supervisor / Kill-on-close-Sicherheitsvertrag.
- PR #3: Backtest innerhalb der offiziellen FreqUI, weiterhin exakt dieselbe Botstrategie.
- PR #4: direkte Runtime-Imports, Stale-/Port-8080-Bereinigung und robuste Windows-Startlogik.
- PR #5: Backtest-Navigation neben Theme-Schalter.
- PR #6: Strategie V2, Multi-Timeframe-Regime + ATR-normalisierter Compression-Breakout + schneller `failed_breakout`-Exit.
- PR #7: kritischer Backtest-Datenfehler behoben: ältere Historie wird mit `--prepend` ergänzt und die tatsächliche Freqtrade-Abdeckung wird fail-closed gegen den angeforderten Zeitraum validiert.
- PR #8: V3 „confirmed breakout“ wurde **nicht gemerged** und am 15.08.2026 geschlossen, weil BTC und ETH über drei Jahre jeweils 0 Trades und SOL nur 9 Trades erzeugten. V3 war damit klar überfiltert und statistisch unbrauchbar.

## 19.3 Warum die 3-Jahres-Datenprüfung zwingend ist

Am 15.08.2026 fiel auf, dass ein vermeintlicher Drei-Jahres-Test fast genauso schnell lief wie ein Zwei-Jahres-Test. Die Diagnose bestätigte einen echten Fehler: Freqtrade hatte vorhandene Daten nur am aktuellen Ende aktualisiert. Die angeforderte ältere Historie lag vor dem lokalen Datenbeginn und Freqtrade meldete ausdrücklich, dass `--prepend` erforderlich ist. Die ersten vermeintlichen Drei-Jahres-Läufe testeten deshalb tatsächlich nur 733 Tage.

PR #7 behebt genau diesen Fall:

1. vorhandene Daten werden bis heute aktualisiert,
2. ältere fehlende Historie wird zusätzlich mit `--prepend` ergänzt,
3. Freqtrade-Ergebnisfelder `backtest_start`, `backtest_end` und `backtest_days` werden geprüft,
4. unvollständige Historie darf nicht mehr als „Fertig“ angezeigt werden.

Für V2/V3 werden aktuell benötigt:

- ausgewähltes Pair: 15m, 1m, 1h, 4h,
- bei ETH/SOL zusätzlich BTC/USDT 4h als Marktregime,
- 75 Tage Download-Warmup vor dem sichtbaren Testfenster,
- 1m nur als Detail-Timeframe für realistischere Intracandle-Fills/Stops/Callbacks; die Strategie entscheidet weiterhin auf geschlossenen 15m-Kerzen.

Die Backtest-Oberfläche muss diese vier Timeframes transparent benennen. Ein Codex-Agent darf die Dateigröße eines Feather-Datasets **nicht** als Beweis für Vollständigkeit verwenden. Maßgeblich sind erste/letzte Kerze, Kerzenzahl, Sortierung, Duplikate und relevante Lücken je Pair/Timeframe sowie der tatsächlich von Freqtrade simulierte Zeitraum.

## 19.4 Autoritative V1-Baseline

Die ursprüngliche Compression-Breakout-Baseline war über ungefähr zwei Jahre netto negativ:

| Pair | Trades | Netto | Profit Factor | Kernaussage |
|---|---:|---:|---:|---|
| BTC | 11 | -12,16 USDT / -4,86 % | ~0,006 | praktisch keine tragfähige Edge |
| ETH | 53 | -19,73 USDT / -7,89 % | ~0,55 | ROI-Gewinner vorhanden, Fehler-Exits dominieren |
| SOL | 158 | -73,33 USDT / -29,33 % | ~0,51 | zu viele schlechte Breakouts |

Counterfactual-Tests mit einfachen festen TP-/SL-Werten und Cooldowns reparierten die Strategie nicht. Auch ohne Gebührenproxy war das aggregierte Signalbild nicht überzeugend. Deshalb darf Codex nicht wieder nur Stoploss/Take-Profit auf derselben schlechten Entry-Familie feinjustieren.

## 19.5 V2: korrekt validierter 3-Jahres-Test

Nach PR #7 wurde V2 auf **1095 Tagen vom 16.08.2023 bis 15.08.2026** erneut getestet:

| Pair | Trades | Netto | Rendite | PF | Winrate | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| BTC/USDT | 14 | -1,51 USDT | -0,60 % | 0,80 | 35,71 % | 1,67 % |
| ETH/USDT | 59 | -29,04 USDT | -11,62 % | 0,25 | 16,95 % | 12,42 % |
| SOL/USDT | 132 | -44,66 USDT | -17,86 % | 0,52 | 21,21 % | 19,99 % |

Trade-Level-Diagnose über alle drei isolierten Pair-Backtests:

- 205 Trades gesamt,
- 146 `failed_breakout`-Exits,
- diese 146 Fehlbreakouts verlieren zusammen ungefähr **-126,14 USDT**,
- kein einziger `failed_breakout` war Gewinner,
- Median-Haltedauer dieser Fehlergruppe ungefähr 39,5 Minuten,
- 38 ROI-Exits gewannen zusammen ungefähr **+62,16 USDT** und alle 38 waren Gewinner.

Schlussfolgerung: Das dominante Problem ist **Entry-Qualität / False Breakouts**, nicht ein zu weiter Hard-Stop. Der schnelle Exit begrenzt Schaden, erzeugt aber keine Edge.

## 19.6 V3 wurde objektiv verworfen

V3 wartete nach einem V2-Setup eine zusätzliche geschlossene 15m-Bestätigung ab und verschärfte 1h-/4h-Trendbedingungen. Exakter Drei-Jahres-Test:

| Pair | Trades | Netto | PF | Max DD |
|---|---:|---:|---:|---:|
| BTC/USDT | 0 | 0,00 USDT | 0,00 | 0,00 % |
| ETH/USDT | 0 | 0,00 USDT | 0,00 | 0,00 % |
| SOL/USDT | 9 | +3,75 USDT / +1,50 % | 1,71 | 0,88 % |

Das positive SOL-Ergebnis ist mit nur neun Trades **kein belastbarer Profitabilitätsnachweis**. BTC/ETH wurden vollständig abgewürgt. PR #8 bleibt geschlossen und ungemerged. Diese Variante darf nicht später aufgrund des positiven SOL-Prozentsatzes fälschlich als Champion bezeichnet werden.

## 19.7 Aktuelle Forschungsrichtung: V4 Trend-Pullback/Reclaim

Nach dem Scheitern zweier Breakout-Varianten wurde die Strategiehypothese strukturell geändert. Forschungsbranch:

`agent/strategy-v4-trend-pullback`

V4 bleibt dieselbe Strategy-Klasse und derselbe Sicherheits-/Backtestpfad, kauft aber **keinen ersten Breakout**. Die Hypothese ist:

- 15m/1h/4h bestätigter Aufwärtstrend,
- Pullback in Richtung 15m EMA20/EMA50,
- anschließend bullischer Reclaim auf einer vollständig geschlossenen 15m-Kerze,
- ETH/SOL nur bei unterstützendem BTC-4h-Regime,
- keine Future-/MFE-Information in Entrybedingungen,
- konservatives Gebührenmodell bleibt unverändert.

V4 ist bis zu einem erfolgreich abgeschlossenen exakten Backtest **Research, nicht main und nicht freigegeben**.

Ein GitHub-Actions-Research-Runner wurde vorbereitet, um 1m/15m/1h/4h-Daten zu validieren und anschließend BTC/ETH/SOL einzeln, gemeinsam sowie in Jahresslices zu testen. GitHub-hosted Runner erhielten zunächst HTTP 451 von `api.binance.com`. Für Research darf deshalb ausschließlich Binances offizieller **Market-Data-Only**-Pfad `data-api.binance.vision` verwendet werden; dies ist kein Grund, Produktions-/Live-URLs stillschweigend umzuschreiben. CCXT muss für diesen Research-Pfad außerdem auf Spot-Märkte begrenzt werden, sonst lädt `fetch_markets()` standardmäßig auch derivative Markt-Metadaten.

## 19.8 Methodik für alle weiteren Strategieiterationen

Codex soll **nicht** blind „so lange optimieren bis Plus herauskommt“. Ab jetzt gilt:

1. Eine ökonomisch/marktstrukturell begründete Hypothese formulieren.
2. Nur ein frühes Developmentfenster für Parameter-/Ideenwahl benutzen.
3. Kandidaten einfrieren.
4. Getrennte Jahresslices/Walk-Forward prüfen.
5. Finalen Holdout nicht wiederholt zur Parameterwahl missbrauchen.
6. Kandidaten mit 0 oder nur sehr wenigen Trades nicht als Erfolg werten.
7. Positive Rendite allein reicht nicht; Profit Factor, Drawdown, Tradezahl, zeitliche Stabilität und Kostensensitivität müssen gemeinsam überzeugen.
8. Final immer den **exakten aktuellen Botcode** über den normalen Backtestpfad und danach im Paper-Forward-Test prüfen.

Momentum-/Trendinformationen dürfen als Hypothese genutzt werden, weil es dokumentierte Krypto-Zeitreihen-Momentum-Effekte gibt. Das ist aber kein Beweis, dass eine konkrete Strategie nach Gebühren profitabel sein wird. Realistische Kosten können vermeintliche Momentum-Edges vollständig aufzehren.

## 19.9 Bekannte Grenzen des aktuellen klassischen Backtests

Auch der korrigierte Backtest ist kein perfektes Live-Replay:

- Freqtrade arbeitet auf historischen OHLCV-Kerzen; echte historische Orderbuchposition, Netzwerklatenz und exakte Limit-Fill-Warteschlange sind nicht rekonstruierbar.
- 1m-Detaildaten verbessern Intracandle-Simulation, ersetzen aber keine Tick-/Orderbuchhistorie.
- `--fee 0.002` wird als konservativer Kostenproxy pro Seite verwendet. Das ist bewusst strenger als nur eine nominelle Maker-/Taker-Gebühr, aber nicht identisch mit jedem realen Fill.
- Die Runtime-DB-/Filesystem-Entry-Guards laufen absichtlich nur in `live`/`dry_run`. Der globale Runtime-Tagesverlust-Guard von 10 USDT wird deshalb im klassischen isolierten Pair-Backtest nicht direkt aus der Paper-DB reproduziert.
- Die normale Backtest-UI testet jeweils ein Pair. Der echte Bot teilt 250 USDT und globale Protections über BTC/ETH/SOL. Vor einer Kapitalfreigabe ist daher zusätzlich ein **gemeinsamer Drei-Pair-Portfolio-Backtest** erforderlich.

Diese Grenzen müssen in Berichten genannt werden; sie dürfen nicht als „perfekter Live-Beweis“ verkauft werden.

## 19.10 Kapital-Skalierung

Die Reihenfolge 250 -> 500 -> 750 -> 1000 USDT ist nur eine spätere **Freigabestufe**, kein Ziel, das einen Backtest erzwingen darf.

Bis auf Weiteres bleibt die Sicherheitskonfiguration bei 250 USDT. Erhöhung erst nach:

- positiver und hinreichend großer Trade-Stichprobe,
- PF deutlich über 1 (als Research-Ziel eher >= 1,2 als bloß 1,01),
- kontrolliertem Drawdown,
- positiver/vertretbarer Performance in getrennten Zeitfenstern,
- Kosten-Stresstest,
- gemeinsamem Portfolio-Test,
- anschließendem ausreichend langen Paper-Forward-Test.

Risk-Limits werden bei späterer Skalierung **nicht automatisch proportional vervielfacht**. Sie werden aus gemessener Verlustverteilung/Drawdown und gewünschtem Risiko neu abgeleitet.

## 19.11 Nächste verbindliche Arbeitsschritte für Codex

1. Zuerst Datenintegrität und exakten Testzeitraum beweisen; niemals aus ZIP-/Feather-Dateigröße schließen.
2. V4-Researchlauf bzw. dessen Nachfolger vollständig auswerten. Falls V4 kein robustes Plus liefert: Hypothese verwerfen/ändern, nicht den Holdout totoptimieren.
3. Backtest-UI soll tatsächlichen Zeitraum/Tagzahl und benötigte Timeframes transparent anzeigen.
4. Eine kombinierte BTC+ETH+SOL-Portfolio-Auswertung ergänzen, ohne eine zweite Strategie einzuführen.
5. Optional Freqtrade `lookahead-analysis` und `recursive-analysis`/geeignete Kausalitätschecks in den Research-Gate aufnehmen; dabei beachten, dass Lookahead-Analysis eigene Backtestparameter erzwingen kann und daher **kein** Ersatz für den autoritativen normalen Backtest ist.
6. Erst nach robustem Kandidaten Paper-Forward-Test starten; Echtgeld bleibt gesperrt.

Dieser Abschnitt hat bei Widerspruch mit älteren Planungsformulierungen Vorrang, sofern die älteren Formulierungen nicht eine strengere Sicherheitsgrenze setzen.

