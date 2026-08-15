from pathlib import Path

report = Path('docs/V8_PAPER_CANDIDATE_REPORT_DE.md')
s = report.read_text(encoding='utf-8')
old = '''## 6-Jahres-Gate

Der durchgehende 6-Jahres-/Kosten-Gate-Lauf ist zum Zeitpunkt dieser ersten Berichtsversion noch in GitHub Actions aktiv. **V8 wird nicht allein aufgrund dieses Dokuments freigegeben.** Vor Merge des Paper-Kandidaten muss dieses Gate ausgewertet und dieser Abschnitt mit dem tatsächlichen Ergebnis ergänzt werden.
'''
new = '''## Durchgehender 6-Jahres-Gate-Test 15.11.2020–15.08.2026

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
'''
if old not in s:
    raise SystemExit('pending six-year report section not found')
s = s.replace(old, new, 1)
s = s.replace(
    '''## Freigabestatus

Bis alle finalen Gates grün sind, gilt:

**Research bestanden genug für einen Paper-Kandidaten – nicht für Echtgeld.**''',
    '''## Freigabestatus

Das historische Research-Gate einschließlich des durchgehenden 6-Jahres-Tests ist abgeschlossen. Der Kandidat erfüllt damit die Anforderungen für den **nächsten unveränderten Paper-Forward-Test mit 250 virtuellen USDT**.

**READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**''',
    1,
)
report.write_text(s, encoding='utf-8')

codex = Path('CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md')
s = codex.read_text(encoding='utf-8')
old = '''## 23.12 6-Jahres-Gate

Zum Zeitpunkt des ersten Schreibens dieses Abschnitts läuft der durchgehende 6-Jahres-Test einschließlich gemeinsamem Portfolio und zusätzlichem 0,4-%-Kostenlauf noch. **Vor Merge des V8-Paper-Kandidaten muss dieser Abschnitt mit den echten Ergebnissen ersetzt werden.**
'''
new = '''## 23.12 Durchgehender 6-Jahres-Gate-Test abgeschlossen

Exakter Zeitraum: 15.11.2020–15.08.2026, 2099 Freqtrade-Tage, unveränderter V8-SHA `9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`.

| Lauf | Trades | Rendite | PF | Max DD |
|---|---:|---:|---:|---:|
| BTC | 45 | +21,413 % | 1,804 | 16,10 % |
| ETH | 44 | +56,080 % | 2,716 | 6,68 % |
| SOL | 47 | +80,011 % | 2,781 | 7,41 % |
| gemeinsames Portfolio | 136 | **+157,504 %** | **2,511** | **8,63 %** |

Portfolio bei 0,2 % Kostenproxy je Seite: +393,76 USDT, schlechtester realisierter Close-Tag ungefähr -9,42 USDT. Portfolio bei 0,4 % je Seite: **+142,274 %, PF 2,209, MaxDD 10,17 %**, schlechtester Close-Tag ungefähr **-10,04 USDT**.

Wichtige Interpretation: Der Runtime-Tagesverlustguard blockiert neue Entries nach <= -10 USDT bereits geschlossenem Tages-P/L. Der klassische Backtest reproduziert diesen DB-Guard nicht identisch. Deshalb ist besonders der 0,4-%-Stresslauf nach einem solchen Grenztag nicht als perfekte Runtime-Parität zu lesen. Bei der normalen 0,2-%-Research-Annahme wurde die -10-USDT-Schwelle im historischen Close-Day-Minimum nicht erreicht.

6-Jahres-Exitbeiträge des Portfolios: 80 `failed_4h_breakout` etwa -156,33 USDT, 19 Hard-Stops etwa -89,38 USDT, 24 `slow_trend_exit` etwa +118,87 USDT, 13 ROI-Exits etwa +520,60 USDT. Die seltenen großen Gewinner bleiben damit zentral für die Edge.

**Folgerung:** V8 ist historisch robust genug für einen erweiterten Paper-Forward-Test, nicht für Echtgeld. Kapital bleibt 250 virtuelle USDT.
'''
if old not in s:
    raise SystemExit('pending six-year codex section not found')
s = s.replace(old, new, 1)
codex.write_text(s, encoding='utf-8')
