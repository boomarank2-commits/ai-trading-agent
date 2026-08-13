# PaperTrendBreakout250V1 – Forschungs- und Forward-Test-Stand

## Hypothese

Auf geschlossenen 1-Stunden-Kerzen wird long eingestiegen, wenn der Schlusskurs
das vorherige, um eine Kerze verschobene 72-Stunden-Hoch um 0,1 Prozent
überschreitet. EMA 50 liegt über EMA 200, EMA 200 steigt gegenüber vor 24
Stunden, ADX(14) ist mindestens 20, ATR(14)/Close liegt zwischen 0,3 und 5
Prozent, das Volumen ist mindestens 1,2-mal so hoch wie der verschobene
24-Stunden-Mittelwert und die Kerze schließt positiv.

Der Exit erfolgt beim Schluss unter dem verschobenen 12-Stunden-Tief oder beim
Kreuzen des Schlusskurses unter EMA 50. Zusätzlich gelten ROI 8 Prozent ab
Entry (mit semantisch gleichen Stützpunkten bei 120 und 360 Minuten), 4 Prozent
nach 1 Tag und 0 Prozent nach 3 Tagen sowie Stop-Loss −5,5
Prozent. Der Backtest-Kostenansatz beträgt wie bei der bestehenden Prüfung 0,2
Prozent je Seite als Proxy für Gebühren und Slippage.

## Retrospektiver Stresstest (kein Gewinnbeweis)

Zeitraum: 28.08.2024 bis 12.08.2026; BTC/USDT, ETH/USDT, SOL/USDT.

| Kennzahl | Ergebnis |
| --- | ---: |
| Trades | 207 |
| Gewinn/Verlust | −24,65 USDT (−9,86 %) |
| Profit Factor | 0,890 |
| Gewinnquote | 35,3 % |
| Maximaler Drawdown | 50,42 USDT (18,31 %) |
| SOL/USDT | +21,32 USDT, PF 1,30 |
| ETH/USDT | −14,71 USDT, PF 0,83 |
| BTC/USDT | −31,26 USDT, PF 0,53 |

Die Hypothese war im Gesamtzeitraum negativ. Sie wird nicht als profitabel,
validiert, holdout-bestanden oder für Echtgeld geeignet bezeichnet.

Ein zusätzlicher reproduzierbarer Smoke-Backtest mit den lokal vorhandenen
15-Minuten-Detaildaten, `--fee 0.002`, aktivierten Protections, ohne Cache und
ohne Export ergab für 01.08.2026 bis 12.08.2026 zwei Trades und −0,477 USDT
(−0,19 Prozent). Er prüft die technische Ausführbarkeit, nicht die Zukunft.

## Forward-Test-Status

- Separater Paper-Forward-Test: beginnt erst mit dem ersten Start dieser Version.
- Holdout: **0 Trades / nicht durchgeführt**.
- Letzte 30 Tage des retrospektiven Datensatzes: 14 rohe Entry-Signale
  (BTC 5, ETH 5, SOL 4). Das ist nur eine Aktivitätsschätzung; ROI, Exit,
  Schutzsperren und bereits belegte Slots können die tatsächliche Zahl senken.
- Erwartung: häufiger als die bisherige 15-Minuten-Kompressions-Baseline, aber
  auch mehrere Tage ohne Trade sind möglich.

## Harte Betriebsgrenze

Diese Klasse verweigert in `bot_start()` und `confirm_trade_entry()` jeden
Non-Dry-run-Pfad. Sie ist ausschließlich für 250 virtuelle USDT, drei
Long-only-Binance-Spot-Positionen à höchstens 80 USDT und höchstens 240 USDT
Gesamtexposition bestimmt. Nach 10 USDT realisiertem Tagesverlust werden neue
Entries gesperrt. Es gibt keine Echtgeldfreigabe.
