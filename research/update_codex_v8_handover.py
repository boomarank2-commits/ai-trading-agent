from pathlib import Path

p = Path('CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md')
s = p.read_text(encoding='utf-8')

# PR #9 appended a second section 19 after the original numbered plan. Keep all
# content, but make the numbering unambiguous for future agents.
s = s.replace(
    '# 19. Verbindlicher Projektstand nach Backtest-Audit vom 15.08.2026',
    '# 22. Verbindlicher Projektstand nach Backtest-Audit vom 15.08.2026',
)
s = s.replace('## 19.', '## 22.')

phase2 = '### Phase 2 – echten 15m/1m-Historical-Replay bauen'
if phase2 in s and 'Aktualisierung 15.08.2026: Der aktuelle Multi-Timeframe-Backtest' not in s:
    s = s.replace(
        phase2,
        phase2
        + '\n\n**Aktualisierung 15.08.2026:** Der aktuelle Multi-Timeframe-Backtest benötigt nicht mehr nur 15m/1m. Für das ausgewählte Pair werden 15m, 1m, 1h und 4h benötigt; bei ETH/SOL zusätzlich BTC/USDT 4h als Marktregime. 1m bleibt ausschließlich Detail-Timeframe, die Strategy-Signale entstehen weiterhin auf geschlossenen 15m-Candles. Ältere fehlende Historie wird per `--prepend` ergänzt und vor jedem Lauf zusätzlich auf Candle-Abdeckung, Duplikate, Sortierung und Lücken geprüft.\n',
        1,
    )

s = s.replace(
    '## 22.7 Aktuelle Forschungsrichtung: V4 Trend-Pullback/Reclaim',
    '## 22.7 Historische Forschungsrichtung: V4 Trend-Pullback/Reclaim – verworfen',
)
if '## 22.7 Historische Forschungsrichtung' in s and 'V4 wurde nach dieser Übergabe tatsächlich getestet' not in s:
    needle = '## 22.7 Historische Forschungsrichtung: V4 Trend-Pullback/Reclaim – verworfen\n'
    s = s.replace(
        needle,
        needle
        + '\n**Nachtrag:** V4 wurde nach dieser Übergabe tatsächlich getestet und war im gemeinsamen Drei-Pair-Portfolio klar negativ. V4 ist daher keine aktuelle Empfehlung mehr. Die vollständige Schleife V4–V8 und der daraus hervorgegangene V8-Paper-Kandidat stehen verbindlich in Abschnitt 23.\n',
        1,
    )

marker = '# 23. Forschungsloop V4–V8 und aktueller Paper-Kandidat'
if marker not in s:
    s = s.rstrip() + r'''

---

# 23. Forschungsloop V4–V8 und aktueller Paper-Kandidat

Dieser Abschnitt ergänzt den Backtest-Audit aus Abschnitt 22. Er dokumentiert die nachfolgenden Strategieexperimente **einschließlich der verworfenen Varianten**. Ein späterer Codex-Agent darf nicht nur V8 sehen und daraus schließen, dass der Weg geradlinig oder garantiert profitabel war.

## 23.1 Verbindliche Methodik

Nach V3 wurde bewusst nicht weiter derselbe 15m-False-Breakout feinoptimiert. Jede neue Variante musste eine nachvollziehbare strukturelle Hypothese besitzen und wurde mit derselben Strategy-Klasse, denselben 250-USDT-Sicherheitsgrenzen und dem exakten Locked-Backtest getestet. Der Research-Pfad verwendet vollständige 1m/15m/1h/4h-Binance-Spot-Daten und zusätzlich gemeinsame BTC/ETH/SOL-Portfolio-Tests. Rohdaten, Backtest-ZIPs und Logs bleiben außerhalb von Git.

Wichtige Regel: **Nicht „optimieren bis Plus erscheint“.** Negative Varianten werden verworfen. Positive Varianten müssen anschließend in älteren/unberührten Zeitfenstern, unter höheren Kosten und danach im Paper-Forward-Test bestehen.

## 23.2 V4–V7: objektiv verworfen

### V4 – 15m Trend-Pullback/Reclaim

Drei-Jahres-Research:

| Pair / Portfolio | Rendite | PF |
|---|---:|---:|
| BTC | -3,443 % | 0,719 |
| ETH | -8,835 % | 0,601 |
| SOL | -23,106 % | 0,629 |
| gemeinsames Portfolio | **-36,248 %** | **0,625** |

Ergebnis: verworfen. Der Wechsel vom direkten Breakout zu einem schnellen 15m-Pullback löste das Kosten-/Entry-Problem nicht.

### V5 – Trend-Pullback mit längerem Gewinner-Horizont

Drei-Jahres-Research: BTC -1,286 %, ETH -12,623 %, SOL -25,151 %, gemeinsames Portfolio **-38,533 %**. Ergebnis: verworfen.

### V6 – langsamer 4h-Momentum-Breakout

Drei-Jahres-Research: BTC -2,649 %, ETH +0,726 %, SOL -19,962 %, gemeinsames Portfolio **-20,687 %**. Ergebnis: verworfen. Ein einzelnes positives Pair genügt nicht.

### V7 – früherer Profit-Lock / engeres Trailing

Gemeinsames Portfolio ungefähr **-24,085 %**. Ergebnis: verworfen. Das frühere Abschneiden von Gewinnern verschlechterte die asymmetrische Trendfolge-Eigenschaft.

## 23.3 V8 – erster belastbarer Paper-Kandidat

Research-Branch: `agent/strategy-v8-slow-donchian`.

V8 wechselt auf eine langsame 4h-Donchian-Trendhypothese:

- frisches 20-Tage-Hoch aus vorherigen 120×4h-Candles;
- 4h EMA50 > EMA200, steigende EMA50, ADX-/RSI-Regime und positives 30-Tage-Momentum;
- 1h EMA50 > EMA200 als zusätzlicher Trendfilter;
- ETH/SOL nur bei positivem BTC-4h-Regime;
- 15m nur als Ausführungs-/Qualitätsebene;
- struktureller 10-Tage-Tief-/Trend-Exit;
- schneller `failed_4h_breakout` nur in jungen Verlusttrades bei echtem Verlust des ursprünglichen 4h-Breakout-Supports;
- Hard-Stop weiterhin -5,5 %;
- keine Positionsaufstockung;
- 250 USDT / maximal 80 USDT je Position / maximal drei Positionen.

Exakter historisch geprüfter Strategy-Quelltext, normalisiert auf LF:

`9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`

**Dieser Fingerprint ist bindend.** Jede Änderung der Strategy-Datei erfordert einen neuen Research-Gate-Lauf.

## 23.4 Unabhängig bewiesene Datenintegrität

Für den Research-Datensatz 01.06.2023 bis 15.08.2026 wurden über Binances offiziellen Public-Market-Data-Pfad je Pair folgende Zeilen geprüft:

| Timeframe | BTC | ETH | SOL |
|---|---:|---:|---:|
| 1m | 1.687.536 | 1.687.537 | 1.687.537 |
| 15m | 112.502 | 112.502 | 112.502 |
| 1h | 28.125 | 28.125 | 28.125 |
| 4h | 7.031 | 7.031 | 7.031 |

Alle zwölf Dateien: 0 Duplikate, 0 nicht-monotone Zeitstempel, 0 fehlende Candle-Intervalle. Damit ist die frühere Sorge wegen einer relativ kleinen Feather-/ZIP-Dateigröße technisch geklärt: Dateigröße ist kein Vollständigkeitskriterium; Zeitstempel, Zeilenzahl, Lückenprüfung und tatsächlicher Freqtrade-Testzeitraum sind maßgeblich.

## 23.5 V8 – exakter 3-Jahres-Research 16.08.2023–16.08.2026

| Lauf | Trades | Rendite | PF | Max DD |
|---|---:|---:|---:|---:|
| BTC | 20 | +20,995 % | 3,386 | 3,07 % |
| ETH | 20 | +22,194 % | 2,827 | 7,58 % |
| SOL | 21 | +17,650 % | 1,875 | 10,91 % |
| gemeinsames Portfolio | 61 | **+60,839 %** | **2,480** | **6,28 %** |

Zeitliche Portfolioslices mit unverändertem Code:

- 2023-08 bis 2024-08: +47,351 %, PF 3,152
- 2024-08 bis 2025-08: +20,170 %, PF 2,528
- 2025-08 bis 2026-08: **-6,100 %**, PF 0,204

Der negative jüngste Slice ist ausdrücklich Teil der Bewertung. V8 ist kein „jedes Jahr Plus“-System.

## 23.6 Vorab festgelegter älterer Holdout 16.08.2021–16.08.2023

Nachdem V8 auf dem späteren Entwicklungsfenster feststand, wurde der ältere Zeitraum geöffnet:

- BTC: -4,873 %, PF 0,404
- ETH: -8,864 %, PF 0,268
- SOL: +30,261 %, PF 4,503
- gemeinsames Portfolio: **+13,324 %, PF 1,483, MaxDD ungefähr 14,05 %**
- erstes Holdout-Jahr: +16,492 %, PF 1,772
- zweites Holdout-Jahr: -0,386 %, PF 0,971

Wichtig: Die Robustheit entsteht teilweise durch das gemeinsame Portfolio. Isolierte BTC-/ETH-Holdouts waren negativ.

## 23.7 Noch älterer, zuvor ungesehener Bestätigungszeitraum

Der feste V8-Code wurde anschließend ohne Parameteränderung auf 15.11.2020–16.08.2021 geprüft:

- BTC +21,658 %, PF 3,348
- ETH +21,425 %, PF 2,680
- SOL +24,886 %, PF 2,579
- Portfolio **+65,970 %, PF 2,840, MaxDD ungefähr 8,13 %**

Das ist ein weiteres positives Robustheitssignal, aber kein Ersatz für Daten aus der Zukunft.

## 23.8 Durchgehender 5-Jahres-Test 16.08.2021–16.08.2026

| Lauf | Trades | Rendite | PF | Max DD |
|---|---:|---:|---:|---:|
| BTC | 29 | +16,306 % | 1,919 | 4,21 % |
| ETH | 32 | +12,480 % | 1,556 | 9,59 % |
| SOL | 38 | +45,309 % | 2,823 | 7,39 % |
| gemeinsames Portfolio | 99 | **+74,095 %** | **2,076** | **14,18 %** |

Portfolio: CAGR ungefähr 11,72 %, Sharpe ~0,824, Sortino ~1,51, Calmar ~0,826. Der von Freqtrade ausgegebene statistische p-Wert lag ungefähr bei 0,091 und damit nicht unter einer klassischen 0,05-Schwelle. Diese Unsicherheit muss sichtbar bleiben.

Jährliche realisierte Beiträge: 2021 Teiljahr +9,85 USDT, 2022 -22,42, 2023 +50,35, 2024 +96,36, 2025 +63,84, 2026 Teiljahr -12,75.

## 23.9 V8 lebt von wenigen großen Trends

5-Jahres-Portfolio:

- 62 `failed_4h_breakout`: ungefähr -112,35 USDT
- 13 Hard-Stops: ungefähr -61,24 USDT
- 19 `slow_trend_exit`: ungefähr +118,70 USDT
- 5 ROI-Exits: ungefähr +240,13 USDT
- längste beobachtete Verlustserie: 23 Trades

Die fünf großen Gewinner übersteigen den gesamten Nettoertrag. Niedrige Trefferquote und lange Verlustserien sind deshalb ein zentrales Risiko des Systems. Codex darf den Paper-Test später nicht nach wenigen Verlusttrades „reparieren“, sonst wird der Forward-Test entwertet.

## 23.10 Kosten-Stresstest

Gemeinsames Portfolio, Entwicklungsfenster:

- 0,1 % je Seite: +63,925 %, PF 2,660
- 0,2 % je Seite: +60,839 %, PF 2,480
- 0,3 % je Seite: +57,753 %, PF 2,318
- 0,4 % je Seite: +54,667 %, PF 2,171

Älterer Holdout:

- 0,1 %: +15,254 %, PF 1,569
- 0,2 %: +13,324 %, PF 1,483
- 0,3 %: +11,395 %, PF 1,405
- 0,4 %: +9,466 %, PF 1,333

Damit blieb die historische Portfolio-Edge auch bei verdoppeltem konservativem Kostenproxy positiv. Dies simuliert trotzdem keine echte historische Limit-Warteschlange.

## 23.11 Kausalität und rekursive Indikatorprüfung

Die Signalmethoden verwenden keine negativen Shifts und keine absolute Last-Row-Adressierung. `get_analyzed_dataframe(...).iloc[-1]` wird in `order_filled()` als Callback verwendet; Freqtrade dokumentiert absolute `iloc`-Nutzung in Callbacks als zulässig, während sie in `populate_*`-Methoden verboten bleibt.

`recursive-analysis` zeigte keine offensichtliche Rekursion der Signalindikatoren. Die 4h EMA200 hat mit dem unveränderten `startup_candle_count=400` eine kleine Anfangswertsensitivität von ungefähr 0,222 %; bei ~799 Startkerzen etwa 0,00015 %, bei 999 praktisch null. Eine Änderung von 400 wäre eine neue Strategy-Version und darf nicht ohne vollständige Neuvalidierung erfolgen.

Freqtrades komplette `lookahead-analysis` ist für V8 derzeit **inconclusive**, nicht „bestanden“. Das Tool verändert absichtlich Wallet/Stake/Protections und standardmäßig die Ordertypen. In Kombination mit V8s hartem 80-USDT-Stake-Cap und Limit-Order-Modell entstand im Harness keine ausreichende Vergleichsstichprobe. Dieses fehlende Tool-Verdikt muss offen dokumentiert bleiben; es ist kein Nachweis eines Bias, aber auch kein zusätzlicher Freibrief.

## 23.12 6-Jahres-Gate

Zum Zeitpunkt des ersten Schreibens dieses Abschnitts läuft der durchgehende 6-Jahres-Test einschließlich gemeinsamem Portfolio und zusätzlichem 0,4-%-Kostenlauf noch. **Vor Merge des V8-Paper-Kandidaten muss dieser Abschnitt mit den echten Ergebnissen ersetzt werden.**

## 23.13 Paper-Promotion nur mit frischer V8-Datenbank

Der Promotion-Branch `agent/promote-v8-paper-candidate` übernimmt exakt den validierten V8-Strategy-Quelltext und isoliert den Forward-Test in:

`runtime/user_data/tradesv8.dryrun.sqlite`

Alte V2/V3-Paper-Daten werden nicht gelöscht, aber nicht mit V8 vermischt. `STARTBOT`, Runtime-Validator und `TESTBOT_AUSWERTUNG` müssen auf dieselbe V8-Datenbank zeigen. Der Runtime-Validator sperrt Abweichungen von ROI `{"0": 0.50}`, Hard-Stop -5,5 %, trailing=false, Stake/Capital/Pair-Regeln und Dry-run weiterhin fail-closed.

## 23.14 Kapital bleibt 250 USDT

Trotz der positiven historischen V8-Ergebnisse bleibt das Kapital zunächst **250 virtuelle USDT**. 500/750/1000 USDT sind keine automatische Folge eines Backtests. Voraussetzung bleibt ein ausreichend langer, unveränderter Paper-Forward-Test plus erneute Risiko-/Drawdownbewertung.

## 23.15 Nächster Agent darf nicht zurückfallen

Ein neuer Codex-Agent soll:

1. V1–V7 nicht erneut als bereits widerlegte Standardideen verkaufen;
2. V8 nicht als Profitgarantie bezeichnen;
3. den Strategy-Fingerprint und die frische V8-Datenbank respektieren;
4. Backtests nur bei bestätigter Candle-Integrität und echter Freqtrade-Zeitabdeckung akzeptieren;
5. gemeinsames BTC/ETH/SOL-Portfolio zusätzlich zu Einzelpaaren prüfen;
6. negative Jahre, Holdout-Schwächen, lange Verlustserien und seltene Gewinner sichtbar halten;
7. erst nach bestandenem Paper-Forward-Test über Echtgeld-/Kapitalskalierung nachdenken;
8. bei jeder Strategy-Codeänderung den gesamten Research-Gate erneut ausführen.

Der ausführliche Zahlenbericht liegt zusätzlich in `docs/V8_PAPER_CANDIDATE_REPORT_DE.md`.
'''+ '\n'

p.write_text(s, encoding='utf-8')
