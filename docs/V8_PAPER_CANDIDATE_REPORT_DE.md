# V8 Slow Donchian – Research- und Paper-Candidate-Bericht

Stand: 15.08.2026

## Status

V8 ist der erste Kandidat dieses Projekts, der nach den verworfenen Varianten V1–V7 in mehreren getrennten historischen Fenstern, im gemeinsamen BTC/ETH/SOL-Portfolio und unter erhöhten Kostenannahmen positiv geblieben ist. Das ist **kein Profitversprechen und keine Echtgeldfreigabe**. V8 ist ausschließlich ein Kandidat für den nächsten sauberen Paper-Forward-Test mit 250 virtuellen USDT.

Der exakte, historisch geprüfte Strategy-Quelltext ist:

- Klasse: `CompressionBreakout250`
- normalisierter LF-SHA256: `9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`
- Spot, long-only
- Basis-/Ausführungstimeframe: 15m
- informative Timeframes: 1h und 4h; bei ETH/SOL zusätzlich BTC 4h
- Startkapital: 250 USDT
- Stake: maximal 80 USDT
- maximal drei Positionen / 240 USDT Gesamtexposition
- Hard-Stop: -5,5 %
- Backtest-Kostenproxy: 0,2 % je Orderseite

Jede Änderung an der Strategy-Datei macht die unten stehenden Zahlen **nicht mehr zu einem Nachweis für den geänderten Code** und verlangt eine vollständige Neuvalidierung.

## Warum V8 entstand

Die frühere 15m-Compression-/Breakout-Familie scheiterte wiederholt an False Breakouts. Im korrekt validierten V2-Drei-Jahres-Test gab es über BTC, ETH und SOL 205 Trades. 146 davon endeten als `failed_breakout`; diese Gruppe verlor rund 126,14 USDT und hatte keinen einzigen Gewinner. 38 ROI-Exits gewannen dagegen zusammen rund 62,16 USDT. V3 versuchte die Breakouts mit einer zusätzlichen 15m-Bestätigung zu filtern, würgte aber BTC und ETH vollständig auf null Trades ab und ließ bei SOL nur neun Trades übrig.

V4–V7 wurden deshalb als Research-Varianten getestet und wieder verworfen. Weder 15m-Trend-Pullback noch langsamere Momentum-Varianten mit engeren Trailing-Exits erreichten einen robust positiven Portfolio-Test.

V8 wechselt strukturell auf einen deutlich langsameren Trendansatz:

1. Ein 4h-Schlusskurs muss ein **frisches 20-Tage-Hoch** über dem vorherigen 120×4h-Donchian-Hoch markieren.
2. 4h EMA50 liegt über EMA200, EMA50 steigt, ADX und RSI müssen in einem plausiblen Trendbereich liegen und 30-Tage-Momentum muss positiv genug sein.
3. 1h EMA50 liegt über EMA200 und steigt.
4. ETH/SOL benötigen zusätzlich ein positives BTC-4h-Regime.
5. Auf 15m wird nur die Ausführungsqualität geprüft; das Signal entsteht nicht aus einem schnellen 15m-Ausbruch.
6. Eine Position wird strukturell beendet, wenn der langsamere Trend bzw. das 10-Tage-Tief bricht. Ein junger Verlusttrade darf zusätzlich in den ersten 48 Stunden als `failed_4h_breakout` beendet werden, wenn der ursprüngliche 4h-Ausbruch klar verloren geht.

Alle rollenden Hochs/Tiefs und Momentumreferenzen verwenden ausschließlich vorherige bzw. bereits geschlossene Kerzen. In Strategy-Callbacks ist `get_analyzed_dataframe(...).iloc[-1]` nur für den zum Callback-Zeitpunkt verfügbaren letzten analysierten Candle-Zustand vorgesehen; in den `populate_*`-Signalmethoden bleibt absolute Last-Row-Adressierung verboten.

## Beweis der Marktdaten-Vollständigkeit

Wegen eines früher entdeckten 733-Tage-Fehltests wurde die Datenprüfung zweifach gehärtet: ältere fehlende Historie wird per `--prepend` ergänzt, danach werden Feather-Dateien vor dem Backtest auf Abdeckung, Reihenfolge, Duplikate und Candle-Lücken geprüft. Nach dem Backtest werden zusätzlich `backtest_start`, `backtest_end` und `backtest_days` aus dem echten Freqtrade-Ergebnis geprüft.

Unabhängiger Research-Download über Binances offiziellen Public-Market-Data-Pfad ergab für den 3-Jahres-Research-Datensatz pro Pair:

| Timeframe | BTC | ETH | SOL |
|---|---:|---:|---:|
| 1m | 1.687.536 | 1.687.537 | 1.687.537 |
| 15m | 112.502 | 112.502 | 112.502 |
| 1h | 28.125 | 28.125 | 28.125 |
| 4h | 7.031 | 7.031 | 7.031 |

In allen zwölf Dateien: 0 Duplikate, 0 unsortierte Zeitstempel und 0 fehlende Candle-Intervalle im geprüften Bereich. Damit ist die geringe Feather-/ZIP-Dateigröße **kein** Hinweis auf fehlende Historie.

## Exakter 3-Jahres-Test 16.08.2023–16.08.2026

| Lauf | Trades | P/L | Rendite | PF | Winrate | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 20 | +52,49 USDT | +20,995 % | 3,386 | 30,0 % | 3,07 % |
| ETH | 20 | +55,49 USDT | +22,194 % | 2,827 | 20,0 % | 7,58 % |
| SOL | 21 | +44,13 USDT | +17,650 % | 1,875 | 23,8 % | 10,91 % |
| gemeinsames Portfolio | 61 | **+152,10 USDT** | **+60,839 %** | **2,480** | 24,6 % | **6,28 %** |

Getrennte Portfolioperioden mit unverändertem Code:

- 16.08.2023–16.08.2024: +47,351 %, PF 3,152
- 16.08.2024–16.08.2025: +20,170 %, PF 2,528
- 16.08.2025–16.08.2026: -6,100 %, PF 0,204

V8 ist also **nicht jedes Jahr profitabel**. Das negative jüngste Jahr ist ein zentraler Risikohinweis und darf nicht versteckt werden.

## Vorab festgelegter älterer Holdout 16.08.2021–16.08.2023

Dieser Zeitraum wurde erst geöffnet, nachdem V8 auf dem späteren Entwicklungsfenster feststand:

| Lauf | Trades | Rendite | PF |
|---|---:|---:|---:|
| BTC | 13 | -4,873 % | 0,404 |
| ETH | 12 | -8,864 % | 0,268 |
| SOL | 13 | +30,261 % | 4,503 |
| gemeinsames Portfolio | 38 | **+13,324 %** | **1,483** |

Jahresslices:

- erstes Holdout-Jahr: +16,492 %, PF 1,772
- zweites Holdout-Jahr: -0,386 %, PF 0,971

Damit hängt die Robustheit teilweise von Diversifikation zwischen den drei Coins ab; BTC und ETH sind im Holdout isoliert negativ.

## Noch älterer, zuvor ungesehener Bestätigungszeitraum 15.11.2020–16.08.2021

Ohne Parameteränderung:

| Lauf | Rendite | PF |
|---|---:|---:|
| BTC | +21,658 % | 3,348 |
| ETH | +21,425 % | 2,680 |
| SOL | +24,886 % | 2,579 |
| gemeinsames Portfolio | **+65,970 %** | **2,840** |

Dieser zusätzliche, chronologisch frühere Zeitraum unterstützt die Hypothese, ersetzt aber keinen zukünftigen Paper-Forward-Test.

## Durchgehender 5-Jahres-Test 16.08.2021–16.08.2026

| Lauf | Trades | P/L | Rendite | PF | Max DD |
|---|---:|---:|---:|---:|---:|
| BTC | 29 | +40,77 USDT | +16,306 % | 1,919 | 4,21 % |
| ETH | 32 | +31,20 USDT | +12,480 % | 1,556 | 9,59 % |
| SOL | 38 | +113,27 USDT | +45,309 % | 2,823 | 7,39 % |
| gemeinsames Portfolio | 99 | **+185,24 USDT** | **+74,095 %** | **2,076** | **14,18 %** |

Portfolio-Kennzahlen aus Freqtrade: CAGR etwa 11,72 %, Sharpe etwa 0,824, Sortino etwa 1,51 und Calmar etwa 0,826. Der von Freqtrade ausgegebene statistische p-Wert lag ungefähr bei 0,091 und damit **nicht** unter einer klassischen 0,05-Schwelle. Die Stichprobe bleibt begrenzt.

Jährliche realisierte P/L-Beiträge waren grob: 2021 Teiljahr +9,85 USDT, 2022 -22,42, 2023 +50,35, 2024 +96,36, 2025 +63,84, 2026 Teiljahr -12,75. Auch hier sind negative Phasen real vorhanden.

## Abhängigkeit von seltenen Gewinnern

Der Ansatz hat absichtlich eine niedrige Trefferquote. Im 5-Jahres-Portfolio kamen die Exit-Beiträge ungefähr aus:

- `failed_4h_breakout`: 62 Trades, -112,35 USDT
- Hard-Stop: 13 Trades, -61,24 USDT
- `slow_trend_exit`: 19 Trades, +118,70 USDT
- ROI: 5 Trades, +240,13 USDT

Die fünf großen ROI-Gewinner übersteigen damit den gesamten Nettoertrag. Die längste beobachtete Verlustserie lag bei 23 Trades. Das ist **kein Bug**, sondern das zentrale Verhaltensrisiko eines Trendfolgeansatzes: längere Verlustserien müssen ausgehalten werden, während wenige große Trends die Verluste kompensieren. Ein Paper-Test, der nach einigen Verlusten vorschnell abgebrochen oder manuell verändert wird, wäre kein fairer Forward-Test dieser Hypothese.

## Kosten-Stresstest

Entwicklungsfenster 2023–2026, gemeinsames Portfolio:

| Kostenproxy je Seite | Rendite | PF | Max DD |
|---:|---:|---:|---:|
| 0,1 % | +63,925 % | 2,660 | 5,71 % |
| 0,2 % | +60,839 % | 2,480 | 6,28 % |
| 0,3 % | +57,753 % | 2,318 | 6,83 % |
| 0,4 % | +54,667 % | 2,171 | 7,39 % |

Älterer Holdout 2021–2023:

| Kostenproxy je Seite | Rendite | PF | Max DD |
|---:|---:|---:|---:|
| 0,1 % | +15,254 % | 1,569 | 13,14 % |
| 0,2 % | +13,324 % | 1,483 | 14,05 % |
| 0,3 % | +11,395 % | 1,405 | 14,94 % |
| 0,4 % | +9,466 % | 1,333 | 14,92 % |

Das ist ein positives Robustheitssignal gegen moderate Kostenverschlechterung, aber keine Garantie für reale Limit-Fills oder Slippage.

## Kausalitäts-/Startup-Prüfung

`recursive-analysis` zeigte keine offensichtlichen rekursiven Probleme in den Signalindikatoren; bei 4h EMA200 bestand mit `startup_candle_count=400` eine kleine Startwertsensitivität von ungefähr 0,222 %, die bei rund 799 Startkerzen auf etwa 0,00015 % und bei 999 praktisch auf null fiel. Der bereits validierte V8-Hash bleibt vorerst bei 400; eine Änderung des Startup-Werts wäre eine neue Variante und verlangt einen neuen vollständigen Test.

Freqtrades vollständige `lookahead-analysis` konnte für diesen Kandidaten **nicht als bestanden gewertet werden**. Das Werkzeug verändert absichtlich Wallet, Stake, Protections und standardmäßig Ordertypen; in Kombination mit dem hart auf 80 USDT begrenzten `custom_stake_amount()` und dem Limit-Order-Modell entstand im Analyse-Harness keine ausreichende Vergleichsstichprobe. Der Test ist daher *inconclusive*, nicht positiv und nicht negativ. Die Signalmethoden werden zusätzlich statisch darauf geprüft, keine negativen Shifts oder absolute Last-Row-Zugriffe zu verwenden. Freqtrades dokumentierte Callback-Nutzung von `get_analyzed_dataframe(...).iloc[-1]` bleibt nur in zeitpunktgebundenen Callbacks erlaubt.

## Durchgehender 6-Jahres-Gate-Test 15.11.2020–15.08.2026

Das finale historische Gate wurde mit **demselben Strategy-Fingerprint** `9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280` und vollständigen, lückenfrei validierten 1m/15m/1h/4h-Daten ausgeführt. Der tatsächlich von Freqtrade simulierte Zeitraum war 15.11.2020 00:00 UTC bis 15.08.2026 22:00 UTC (`backtest_days=2099`).

| Lauf | Trades | P/L | Rendite | PF | Winrate | Max DD | schlechtester Close-Tag |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTC | 45 | +53,53 USDT | +21,413 % | 1,804 | 20,0 % | 16,10 % | -4,71 USDT |
| ETH | 44 | +140,20 USDT | +56,080 % | 2,716 | 20,5 % | 6,68 % | -4,71 USDT |
| SOL | 47 | +200,03 USDT | +80,011 % | 2,781 | 23,4 % | 7,41 % | -4,71 USDT |
| gemeinsames Portfolio | 136 | **+393,76 USDT** | **+157,504 %** | **2,511** | 21,3 % | **8,63 %** | **-9,42 USDT** |

Exit-Beiträge des gemeinsamen 6-Jahres-Portfolios:

- `failed_4h_breakout`: 80 Trades, ungefähr -156,33 USDT
- Hard-Stop: 19 Trades, ungefähr -89,38 USDT
- `slow_trend_exit`: 24 Trades, ungefähr +118,87 USDT
- ROI: 13 Trades, ungefähr +520,60 USDT

Die längste Verlustserie blieb bei 23 Trades. Auch im längeren Fenster bleibt die Strategie also stark asymmetrisch: viele kleine/mittlere Verluste werden von wenigen großen Trends getragen.

Zusätzlich wurde derselbe 6-Jahres-Portfolio-Test mit **0,4 % Kostenproxy je Orderseite** ausgeführt. Ergebnis: 136 Trades, **+142,274 %**, PF **2,209**, MaxDD **10,17 %**. Der schlechteste realisierte Close-Tag lag dabei bei ungefähr **-10,04 USDT** und überschreitet damit knapp die Runtime-Grenze von -10 USDT Tagesverlust. Der klassische Backtest simuliert den datenbankbasierten globalen Tagesverlust-Guard nicht identisch; bei dieser extrem konservativen Kostenannahme würde der tatsächliche Paper-/Runtime-Pfad nach Erreichen der Grenze neue Entries blockieren und könnte daher vom klassischen Ergebnis abweichen. Bei der normalen Research-Annahme von 0,2 % je Seite lag der schlechteste Close-Tag mit ungefähr -9,42 USDT noch oberhalb der Stop-Grenze.

Dieses 6-Jahres-Gate stärkt die historische Evidenz deutlich, beseitigt aber die bekannten Risiken **nicht**: einzelne negative Jahre, niedrige Trefferquote, lange Verlustserien, starke Abhängigkeit von wenigen großen Gewinnern und die fehlende echte historische Orderbuch-/Latenzsimulation bleiben bestehen.

## Paper-Forward-Vertrag

Für den nächsten Forward-Test wird eine neue Datenbank `runtime/user_data/tradesv8.dryrun.sqlite` verwendet. Die alte V2/V3-Datenbank wird nicht gelöscht, aber nicht mit V8 vermischt. STARTBOT, Runtime-Validator und Reporter zeigen auf dieselbe V8-Datenbank.

Der Paper-Test bleibt bei 250 virtuellen USDT. Eine Erhöhung auf 500/750/1000 ist **nicht** Teil dieser Promotion. Skalierung wird erst nach einem ausreichend langen unveränderten Forward-Test und erneuter Risikoprüfung diskutiert.

## Bekannte Grenzen

- Historische OHLCV-Daten rekonstruieren keine echte Orderbuch-Warteschlange, Netzwerklatenz oder Tickfolge.
- 1m-Detaildaten verbessern Intracandle-Fills/Callbacks, machen den Backtest aber nicht zu einem perfekten Live-Replay.
- Der globale 10-USDT-Tagesverlustguard basiert im laufenden Bot auf der Paper-Datenbank und wird im klassischen Backtest nicht identisch aus einer historischen Runtime-DB wiedergegeben.
- Historische Ergebnisse können sich in zukünftigen Marktregimen vollständig verschlechtern.
- Die geringe Tradezahl und die Abhängigkeit von wenigen großen Gewinnern erhöhen die statistische Unsicherheit.

## Freigabestatus

Das historische Research-Gate einschließlich des durchgehenden 6-Jahres-Tests ist abgeschlossen. Der Kandidat erfüllt damit die Anforderungen für den **nächsten unveränderten Paper-Forward-Test mit 250 virtuellen USDT**.

**READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**
