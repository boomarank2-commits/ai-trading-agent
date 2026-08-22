# V12.16 – vorab registrierte ADA-Universumserweiterung

Status: **REJECT_BACKTEST – V12.15 technisch wiederhergestellt**.

Die Teile bis einschließlich der PASS-Grenzen wurden vor Codeänderung und
Backtest geschrieben. Das Ergebnis darunter wurde erst nach Abschluss des
einzigen Laufs ergänzt; kein Gate wurde verändert.

## Ausgangspunkt

V12.15 ist der aktive Rückfallstand. Sein einziger exakter Drei-Jahres-Lauf
endete bei 545,409 USDT (+295,409 USDT), 122 Trades, Profit Factor 2,5554,
8,19 % geschlossenem Max-Drawdown, 23,07 % Kapitalzeit und 61,33 % Zeit ohne
Position. Alle sechs Märkte waren positiv.

## Genau eine Änderung

V12.16 ergänzt ausschließlich `ADA/USDT` als siebten Spot-Markt. ADA verwendet
unverändert die bestehende Broad-Core-Logik von SOL/XRP/BNB/DOGE. Nicht
verändert werden:

- Entries, Indikatoren und Schwellen;
- ROI, Stoploss und der späte Champion-Profit-Ratchet;
- Protections und Cooldowns;
- 250 USDT Startkapital, 80 USDT Stake und drei maximale Positionen;
- 0,2 % Gebühren je Seite, 1m-Detail und drei Jahre Testzeitraum;
- BTC/ETH-Reclaim-Zuordnung.

Es gibt ausdrücklich kein ADA-spezifisches Tuning. Die öffentliche
Binance-Spot-Liquiditätsprüfung und die Auswahl von ADA erfolgten, bevor ein
ADA-Strategieergebnis betrachtet wurde.

## Falsifizierbare Hypothese

Ein siebter reifer, liquider Spot-Markt erzeugt zusätzliche unabhängige
Einstiegschancen. Dadurch steigen Kapitalzeit und Gesamtgewinn, ohne Profit
Factor, Drawdown, die sieben positiven Pair-Beiträge oder den Gewinn des
bisherigen Sechs-Pair-Kerns unter die vorab gesetzten Grenzen zu drücken.

## Vorab festgelegte PASS-Grenzen

Der Versuch ist nur PASS, wenn gleichzeitig:

1. Audit mit exakt 28 erwarteten Candle-Sätzen vollständig besteht;
2. Nettogewinn > 295,409 USDT und Endkapital > 545,409 USDT;
3. Profit Factor >= 2,5554;
4. geschlossener Max-Drawdown <= 10 %;
5. Kapitalzeit > 23,07 % und Zeit ohne Position < 61,33 %;
6. jedes der sieben Pairs einen positiven Nettobeitrag liefert;
7. die bisherigen sechs Pairs zusammen >= 288,646 USDT liefern;
8. die ROI-Gewinnquelle erhalten bleibt;
9. sämtliche Tests und Governance-Prüfungen bestehen.

Ein FAIL führt zur vollständigen technischen Rückkehr auf V12.15. Der negative
Versuch bleibt dennoch in Bericht, Ledger und Fingerprint-Sperre erhalten.

## Exakter Lauf

- Run-ID: `20260822T202801Z-699e3b83`
- getesteter Commit: `47257667e350059944893c6899b6b807d3ec238f`
- Strategy-Hash: `9ad6f3e96d0f440a8a9cf4029cb6f64b7f6b73aba6ab524310f192797c1b6acf`
- Logik-Hash: `9ae64e5cdc0a96c6937a0a7e8a3947e019827f381ccc8dc714aee0e6892e9b68`
- Fingerabdruck: `5b791472759974c22f2b5dad4f426247c53c9643938deaa0b7c4c96344510f65`
- Zeitraum: 23.08.2023 bis 22.08.2026, 1095 Tage

Der formale Audit bestand vollständig: exakt 28 erwartete Candle-Sätze,
keine Lücken oder Duplikate, exakte Strategy-/Config-Dateien, keine
unerwarteten Repo-Lesezugriffe, keine veränderten Inputs und keine
Kindprozesse.

## Ergebnis und Gate-Entscheidung

| Kennzahl | V12.15 / Grenze | V12.16 | Gate |
|---|---:|---:|---|
| Endkapital | > 545,409 | 548,135 USDT | PASS |
| Nettogewinn | > 295,409 | 298,135 USDT | PASS |
| Profit Factor | >= 2,5554 | 2,5356 | **FAIL** |
| Trades | Diagnose 122 | 122 | Diagnose |
| Gewinne / Verluste | 23 / 99 | 24 / 98 | Diagnose |
| geschlossener Max-Drawdown | <= 10 % | 11,84 % | **FAIL** |
| Kapitalzeit | > 23,07 % | 24,37 % | PASS |
| Zeit ohne Position | < 61,33 % | 60,50 % | PASS |
| alle sieben Pairs positiv | erforderlich | SOL −1,025 | **FAIL** |
| bisherige sechs zusammen | >= 288,646 | 270,326 USDT | **FAIL** |
| ROI-Quelle | erhalten | 8 Exits / +320,270 | PASS |

Pair-Beiträge: BTC +81,359, ETH +51,952, SOL −1,025, XRP +66,762, BNB
+26,346, DOGE +44,932 und ADA +27,809 USDT.

ADA war isoliert positiv, erhöhte Kapitalzeit und senkte die Leerlaufzeit.
Trotzdem verdrängte die zusätzliche Slot-Konkurrenz wertvollere XRP-/SOL-
Chronologie. Gegenüber V12.15 gewann das Gesamtportfolio nur +2,726 USDT,
während Profit Factor und Drawdown die Qualitätsgrenzen verfehlten und der
bisherige Kern rund 25,083 USDT verlor.

## Entscheidung

V12.16 wird **nicht** übernommen. Strategy, Config, UI, Start-/Downloadpfade,
Validatoren, Anleitungen und aktive Vertragstests wurden auf den exakten
V12.15-Stand zurückgeführt. Der V12.16-Bericht, Ledger-Eintrag, Audit und
Fingerabdruck bleiben erhalten. Derselbe Versuch darf weder identisch noch
durch bloßes ADA-Schwellen-Tuning auf demselben Fenster wiederholt werden.
