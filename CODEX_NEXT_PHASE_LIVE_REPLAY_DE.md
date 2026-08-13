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
