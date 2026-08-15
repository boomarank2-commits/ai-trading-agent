from pathlib import Path

codex = Path('CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md')
text = codex.read_text(encoding='utf-8')
marker = '# 19. Verbindlicher Projektstand nach Backtest-Audit vom 15.08.2026'
if marker not in text:
    block = r'''

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
'''
    text = text.rstrip() + block + '\n'
    codex.write_text(text, encoding='utf-8')

ui = Path('runtime/ui/testbot-backtest.js')
s = ui.read_text(encoding='utf-8')
if 'function balanceMoney(value)' not in s:
    needle = '''  function percent(value) {'''
    insert = '''  function balanceMoney(value) {\n    return `${Number(value || 0).toFixed(2)} USDT`;\n  }\n\n'''
    s = s.replace(needle, insert + needle, 1)
s = s.replace(
    'Beim Start werden die benötigten 15-Minuten- und 1-Minuten-Kerzen direkt aus öffentlichen Binance-Marktdaten geladen bzw. aktualisiert. 1m-Daten dienen nur zur genaueren Fill-/Stop-Simulation; die Strategie entscheidet weiterhin auf ihrem aktuellen 15m-Timeframe.',
    'Beim Start werden 15m-, 1m-, 1h- und 4h-Kerzen direkt aus öffentlichen Binance-Marktdaten geladen bzw. aktualisiert. Für ETH/SOL wird zusätzlich BTC-4h als Marktregime benötigt. 1m dient nur zur genaueren Fill-/Stop-Simulation; Entry-/Exit-Signale entstehen weiterhin auf geschlossenen 15m-Kerzen.'
)
s = s.replace(
    'resultCard("Endkapital", money(r.final_balance_usdt), profitClass),',
    'resultCard("Endkapital", balanceMoney(r.final_balance_usdt), profitClass),'
)
old_note = '''document.getElementById("tb-note").textContent = `Getestet wurde exakt ${r.strategy} mit Strategie-Hash ${String(r.strategy_sha256 || "").slice(0, 16)}… . Ändert sich der Bot-Code, ändert sich dieser Hash und der nächste Backtest verwendet automatisch die neue Version.`;'''
new_note = '''document.getElementById("tb-note").textContent = `Getestet wurde exakt ${r.strategy} mit Strategie-Hash ${String(r.strategy_sha256 || "").slice(0, 16)}… . Tatsächlicher Freqtrade-Zeitraum: ${r.backtest_start || "?"} bis ${r.backtest_end || "?"} (${Number(r.backtest_days || 0)} Tage), serverseitig gegen den angeforderten Zeitraum geprüft. Ändert sich der Bot-Code, ändert sich der Hash und der nächste Backtest verwendet automatisch die neue Version.`;'''
s = s.replace(old_note, new_note)
ui.write_text(s, encoding='utf-8')
