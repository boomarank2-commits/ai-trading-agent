# V12.19 – schnelle Backtests und dauerhafte Pair-Lernakten

Stand: 23.08.2026

Aktive Paper-Strategie: `CompressionBreakout250`, Version `V12.19`

Experiment: `V12.19-PERSISTENT-PAIR-LEARNING-FAST-BACKTEST`

Vorgänger: `V12.18-TEN-PAIR-PROFIT-PYRAMID-REPAIR`
Strategie-SHA-256: `6f0a006a7c459a165105ddf245222d99b27961acfd5ccde47b46181534f256ce`

## Zweck

V12.19 löst zwei voneinander abhängige Probleme:

1. Ein Zehner-Einzelbatch durfte seinen Fortschritt nicht nur im Browser halten.
   Nach Seitenwechsel, Neuladen oder Bot-Neustart muss eindeutig erhalten
   bleiben, welcher Coin bereits mit welcher Botlogik getestet wurde.
2. Der V12.18-Backtest war gegenüber älteren BTC-/ETH-/SOL-Läufen unerwartet
   langsam. Die Ursache musste gemessen und ohne Änderung der simulierten
   Handelsentscheidungen beseitigt werden.

V12.19 ist weiterhin ausschließlich Paper-/Dry-run-Research. Diese technische
Reparatur ist weder ein Profitversprechen noch eine Echtgeldfreigabe.

## Historische Laufzeiten und festgestellter Rückschritt

Erhaltene V12.9-Dreijahresläufe benötigten:

| Pair | Run-ID | Laufzeit |
| --- | --- | ---: |
| BTC/USDT | `20260821T074517Z-ae0029a7` | 4,42 min |
| ETH/USDT | `20260821T075038Z-99a0a7fd` | 3,84 min |
| SOL/USDT | `20260821T075548Z-affff906` | 5,31 min |

Die beobachteten V12.18-Dreijahresläufe benötigten dagegen:

| Pair | Run-ID | Laufzeit |
| --- | --- | ---: |
| BTC/USDT | `20260823T204044Z-1595c655` | 25,28 min |
| ETH/USDT | `20260823T210615Z-1559c5c9` | 14,47 min |

Mehr Coins in der Whitelist erklären diesen Unterschied bei einem pair-lokalen
Einzeltest nicht. Profiling eines exakt festgelegten BTC-Ausschnitts zeigte rund
40,5 Millionen Funktionsaufrufe. Der größte Kostenblock waren wiederholte tiefe
Kopien des kompletten Freqtrade-Trade-Objekts vor benutzerdefinierten Callbacks.

## Technische Ursache

V12.18 hatte Position Adjustment aktiviert. Bei einem Backtest mit
`--timeframe-detail 1m` rief Freqtrade den Adjustment-Pfad für jede offene
Position auf jeder 1-Minuten-Detailkerze auf. Das zusätzliche Entry-Signal der
Strategie stammt jedoch ausschließlich aus dem 15-Minuten-Strategieframe und
kann sich zwischen zwei 15-Minuten-Grenzen nicht ändern.

Damit wurden vierzehn von fünfzehn Adjustment-Prüfungen ohne neue
Entscheidungsmöglichkeit ausgeführt. Zusätzlich erzeugte Freqtrades allgemeiner
Sicherheitswrapper vor `adjust_trade_position`, `custom_stoploss` und
`custom_exit` jeweils eine tiefe Trade-Kopie. Diese drei V12.19-Callbacks lesen
den Trade nur; ihre Mutationsfreiheit ist nun als Testvertrag abgesichert.

## V12.19-Laufzeitreparatur

- `custom_stoploss` und `custom_exit` bleiben auf jeder 1-Minuten-Detailkerze
  aktiv. Intracandle-Stopps und -Exits werden nicht gröber gemacht.
- `adjust_trade_position` wird im Backtest nur auf einer neuen
  15-Minuten-Strategiekerze ausgewertet. Live und Dry-run prüfen weiterhin in
  jedem normalen Botzyklus.
- Der gesperrte Backtest-Runner überspringt die defensive tiefe Kopie nur für
  die drei ausdrücklich registrierten und getesteten read-only Callbacks.
- Die Änderung ist opt-in. Eine spätere Strategie mit 1-Minuten-abhängiger
  Adjustment-Logik erhält diese Abkürzung nicht automatisch.
- Das Backtest-Protokoll wurde versioniert. Alte V12.18-Fingerprints werden
  deshalb nicht fälschlich als identische V12.19-Protokollausführung behandelt.

## Gemessene A/B-Parität

Messfenster: BTC/USDT, `2023-10-01` bis `2024-01-15`, 15m-Strategie,
1m-Detail, Gebühr `0.002`, Protections aktiv, Startwallet 250 USDT.

| Ausführung | Laufzeit | Trades | Gewinn | Rendite | Haltedauer | geschlossener Drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| unveränderte V12.18-Aufrufkette | 193,05 s | 1 | +60,637 USDT | +24,25 % | 76 d 9 h | 0 |
| nur 15m-Adjustment-Cadence | 84,84 s | 1 | +60,637 USDT | +24,25 % | 76 d 9 h | 0 |
| Cadence plus read-only Fastpath | 32,92 s | 1 | +60,637 USDT | +24,25 % | 76 d 9 h | 0 |

Die Endvariante war in diesem gemessenen Ausschnitt 5,86-mal schneller. Die
finanziellen und chronologischen Resultate waren exakt gleich. Das ist ein
technischer Paritätsbeleg für den gemessenen Pfad, noch keine vollständige
finanzielle Bewertung aller zehn Coins.

### Vollständiger BTC-Dreijahres-Paritätslauf mit Zusatzentries

Anschließend wurde der genaue historische BTC-Datensatz des langsamen
V12.18-Laufs `20260823T204044Z-1595c655` erneut verwendet. Alle vier
Candle-Dateien hatten noch exakt die im V12.18-Dateiaudit festgehaltenen
SHA-256-Werte. Zeitraum, Gebühr, Protections, 1m-Detail und 250-USDT-Wallet waren
identisch.

| Kennzahl | V12.18 | V12.19 |
| --- | ---: | ---: |
| Zeitraum | 24.08.2023 bis 23.08.2026 20:00 | identisch |
| Trades | 14 | 14 |
| Entry-Blöcke | 24 | 24 |
| Zusatzentries | 10 | 10 |
| Trades mit mehreren Entries | 5 | 5 |
| Gewinn | +166,6273 USDT | +166,6273 USDT |
| Rendite | +66,6509 % | +66,6509 % |
| Profit Factor | 9,7764 | 9,7764 |
| geschlossener Drawdown | 2,70 % | 2,70 % |
| reine Simulation | ca. 1.468 s | ca. 60 s |
| kompletter neuer Diagnoseprozess | - | 71,3 s |

Damit ist die zeitliche Optimierung ausdrücklich auch für fünf mehrfach
aufgestockte Trades und zehn tatsächliche Zusatzentries paritätsgeprüft. Die
reine Simulation war in diesem vollständigen Fall rund 24,5-mal schneller.
Dieser Lauf bewertet weiterhin nur BTC; die zehn Coins umfassende finanzielle
Matrix bleibt offen.

## Dauerhafter Zehner-Einzelbatch

Der UI-Knopf `Alle 10 einzeln testen` startet ab V12.19 keinen nur im Browser
lebenden JavaScript-Loop mehr. Der lokale FastAPI-Server verwaltet die zehn
Tests und schreibt nach jedem Zustandswechsel:

```text
runtime/user_data/backtest_results/ui/_BATCHES/
  latest.json
  <Batch-ID>/
    batch-plan.json
    batch-result.json
```

`batch-plan.json` hält vor dem ersten Lauf fest:

- exakte Strategieversion und SHA-256;
- Git-Commit;
- Zeitraum und alle zehn Pair-Fingerprints;
- Kapitalinterpretation: zehn unabhängige 250-USDT-Einzelwallets;
- die bereits vorhandene Historie jeder Pair-/Zeitraumzelle.

`batch-result.json` wird nach jedem Coin aktualisiert und enthält Status,
Fortschritt, aktuellen Coin, Fehler sowie die kompakten Resultate aller fertigen
Coins. Nach einem Serverneustart wird ein zuvor laufender Batch als
`interrupted` erkannt. Derselbe Knopf setzt ihn fort. Fertige identische Zellen
werden aus dem erhaltenen Ergebnis übernommen und nicht erneut simuliert.

Ein Batch mit Fehlern kann erneut fortgesetzt werden; nur fehlgeschlagene oder
noch offene Zellen werden wieder angegangen. Ein vollständig fertiger identischer
Batch wird nicht nochmals gestartet.

## Lernakte je Coin und Zeitraum

Nach jedem erfolgreichen Einzeltest erzeugt die Gesamtauswertung zusätzlich:

```text
runtime/user_data/backtest_results/ui/_PAIR_HISTORIEN/
  BTC_USDT-1J.json
  BTC_USDT-1J.md
  ...
  BCH_USDT-3J.json
  BCH_USDT-3J.md
```

Jede Akte enthält:

- alle erhaltenen vollständigen Läufe genau dieser Pair-/Zeitraumzelle;
- den aktuellen Lauf;
- den letzten materiell anderen Vorgänger;
- Strategy-, Logik- und Test-Fingerprint;
- Gewinn, Rendite, Tradezahl, Gewinne/Verluste, Trefferquote, Profit Factor;
- Drawdown, Kapitalzeit, Zeit ohne Position und Entry-Blöcke;
- Deltas zum Vorgänger;
- eine kurze deutsche Einordnung;
- `duplicate_execution_allowed: false`.

Der Run selbst erhält dieselbe `historical_context`-Struktur in
`experiment-result.json` und im UI-Ergebnis. So kann eine spätere GPT-/Codex-
Runde aus dem neuesten Resultat erkennen, was davor getestet wurde und ob die
neue Änderung Gewinn, Aktivität, Drawdown oder Kapitalnutzung verbessert hat.

## Laufzeitaufschlüsselung je Ergebnis

Jeder neue Lauf speichert getrennt:

- `market_data_seconds`: Aktualisieren, Ergänzen und Prüfen der Kerzendaten;
- `simulation_seconds`: eigentliche Freqtrade-Simulation;
- `analysis_seconds`: Audit und Ergebnis-/Historienauswertung;
- `total_seconds`: Gesamtdauer des Jobs.

Damit ist beim nächsten langsamen Lauf sichtbar, ob Binance-Download,
Datenreparatur, Simulation oder Auswertung die Zeit verbraucht. Eine für längere
Zeit unveränderte Prozentanzeige allein gilt nicht mehr als Diagnose.

## Was unverändert bleibt

- zehn Binance-Spot-Paare;
- ein gemeinsames 250-USDT-Wallet im Paperbot;
- höchstens drei aktive 80-USDT-Blöcke beziehungsweise 240 USDT;
- Einzelbacktest: ein Coin mit eigenem 250-USDT-Testwallet;
- Zehner-Einzelbatch: zehn getrennte Walletsimulationen, keine 2.500-USDT-
  Portfoliokurve;
- long-only, 1x, kein Verlust-Nachkauf, kein Martingale;
- zusätzlicher Block nur bei neuem Signal, positivem Trade und höherem Fill;
- Stop-Loss, Reclaims, Donchian-Einstiege und pair-lokale Protections aus V12.18;
- exakter Source-/Config-/Candle-Audit und Sperre identischer Tests.

## Verbindliche nächste Schritte

1. Den laufenden alten V12.18-Batch nicht durch Dateiänderungen auf dem
   Benutzer-PC beeinflussen. Erst nach seinem Ende oder einem bewussten Stopp
   Git pullen und V12.19 neu starten.
2. Einen V12.19-Zehner-Einzelbatch für den gewünschten Zeitraum starten.
3. Nach Abschluss die zehn Pair-Historien und die Zeitaufschlüsselungen lesen.
4. Schwache Coins nicht gemeinsam beliebig verändern. Pro Coin genau eine
   begründete, vorab registrierte und materiell neue Hypothese ableiten.
5. Neue Ergebnisse gegen denselben Pair-/Zeitraumvorgänger vergleichen und
   zusätzlich andere Zeitfenster beziehungsweise Holdout/Walk-Forward prüfen.
6. Erst nach belastbaren Einzelpaarverbesserungen den internen gemeinsamen
   Zehn-Paare-250/3×80-Systemtest und Kostenstress ausführen.
7. Keine Echtgeldpromotion allein aus Backtests oder dieser Laufzeitreparatur.

## Nicht erneut als neues Experiment ausführen

- V12.18 BTC 1 Jahr mit Fingerprint
  `ac857d20608e391c35d9aec4e14e94f13e1dca33666a0e7b3414c83b9666f57a`;
- denselben V12.19-Pair-/Jahres-Fingerprint nach einem Seitenreload;
- bloße Versions-, Kommentar- oder Dokumentationsänderungen ohne materielle
  Strategie- oder Protokolländerung.

Historische Rohresultate bleiben erhalten. V12.18 bleibt als Vorgängerakte in
`V12_18_REPAIR_HANDOFF_DE.md`; sie wird durch V12.19 weder gelöscht noch
umetikettiert.
