# V12.13 – Entfernung des ETH-Reclaims

## Entscheidung

**REJECT_BACKTEST – nicht als aktiven Dry-run-Stand übernehmen.**

Der Versuch war formal gültig, verringerte aber den Gewinn gegenüber V12.12 um
35,875 USDT und den Profit Factor von 2,4833 auf 2,3636. Dass gleichzeitig 18
weniger Verlusttrades entstanden, genügt deshalb nicht für eine Promotion.

## Exakter Versuchsvertrag

- Run: `20260822T121118Z-8c9385d9`
- Strategy-Hash:
  `043916a93ef9aafac3622425496ca2cd75f01c639bb3dc345a79887e882813d9`
- Logik-Hash:
  `506e67a6eed9d44cd93cbcea121190905a647c586339a96ee250c21a82fcf9e8`
- Fingerabdruck:
  `15d9cb240a80169b05020cf115317df54fa4ce66f425223d71bce646dc52c111`
- Zeitraum: 23.08.2023 bis 22.08.2026, 1.095 Tage
- Portfolio: ein gemeinsames Konto mit 250 USDT, 80 USDT je Position, maximal
  drei offene Positionen
- Pairs: BTC, ETH, SOL, XRP, BNB und DOGE gegen USDT
- Spot, long-only, kein Hebel, kein DCA
- 15m-Strategie mit 1m-Detail, 0,002 Gebühr je Orderseite, Protections aktiv,
  Cache aus
- einzige Strategieänderung: ETH aus `RECLAIM_PROFILES` entfernt; BTC-Reclaim
  und alle langsamen Kerne unverändert

## Audit

Der formale Audit bestand vollständig. Der Runner verwendete die exakte
Strategy und beide vorgesehenen Configs. Alle 24 erwarteten Candle-Sätze aus
sechs Pairs mal vier Timeframes wurden beobachtet; es gab keine fehlenden,
zusätzlichen oder während des Laufs veränderten Candle-Dateien. Es gab keine
ungeplanten Repository-Lesezugriffe und keine Kindprozesse im gesperrten
Backtest.

## Ergebnis gegen den Maßstab

| Kennzahl | V12.12 | V12.13 | Differenz |
|---|---:|---:|---:|
| Endkapital | 538,646 | 502,772 | −35,875 USDT |
| Nettogewinn | 288,646 | 252,772 | −35,875 USDT |
| Trades | 122 | 103 | −19 |
| Gewinne / Verluste | 22 / 100 | 21 / 82 | −1 / −18 |
| Profit Factor | 2,4833 | 2,3636 | −0,1197 |
| Sharpe | 0,44 | 0,3716 | niedriger |
| geschlossener Max-Drawdown | 9,62 % | 9,24 % | −0,38 Punkte |
| Kapitalzeit | 23,61 % | 23,42 % | −0,19 Punkte |
| Zeit ohne Position | 61,25 % | 61,06 % | −0,19 Punkte |

## Attribution V12.13

| Pair | Trades | Gewinn | Gewinntrades | Verlusttrades |
|---|---:|---:|---:|---:|
| BTC | 16 | +81,359 USDT | 4 | 12 |
| ETH | 18 | +60,523 USDT | 4 | 14 |
| SOL | 22 | +5,880 USDT | 4 | 18 |
| XRP | 12 | +65,224 USDT | 3 | 9 |
| BNB | 16 | +14,148 USDT | 4 | 12 |
| DOGE | 19 | +25,637 USDT | 2 | 17 |

Die großen Ergebnisquellen blieben wenige lange Trends: sieben ROI-Exits
lieferten +280,212 USDT und 20 langsame Trend-Exits +146,568 USDT. Dem standen
13 Hard-Stop-Exits mit −61,062 USDT und zahlreiche kleine Failed-Breakout-Exits
gegenüber. Ein pauschal engerer Stop oder früheres Take-Profit würde deshalb die
beobachtete Gewinnquelle direkt gefährden.

## Kausale Abweichung von V12.12

92 Trades waren identisch. V12.12 hatte 30 zusätzliche, V12.13 elf andere
Trades. Die entfernten 29 ETH-Reclaims verloren zwar zusammen 22,210 USDT,
hatten aber die pair-lokale ETH-Sperre ausgelöst. Diese Sperre blockierte in
V12.12 einen späteren ETH-Champion-Verlierer und ließ einen Slot für einen
XRP-Gewinner von ungefähr +39,998 USDT frei. V12.13 nahm stattdessen den
ETH-Trade vom 27.11. bis 19.12.2024 mit −2,865 USDT.

Damit ist die Hypothese widerlegt: Die isoliert negative Tag-Summe war keine
valide Schätzung der Änderung im gemeinsamen Wallet. Protections und drei
konkurrierende Slots machen die Portfolioreihenfolge nicht additiv.

## Dauerhaft verworfene direkte Folgeideen

- Kein allgemeiner 36h-/48h-Verlust-Zeitstopp: Die Diagnose hätte rund 76,260
  USDT gekostet und zwei spätere Großgewinner früh beendet.
- Kein ETH-Reclaim-Volumenfilter zwischen 0,70 und 1,25: Er entfernte den
  einzigen positiven ETH-Reclaim, ließ aber ausschließlich Verlierer übrig.
- Den identischen V12.13-Fingerabdruck nie erneut ausführen.

Der nächste isolierte Versuch V12.14 setzt deshalb wieder auf V12.12 auf und
prüft nur eine frühere pair-lokale Verlustpause. Seine Kriterien stehen vor der
Codeänderung in `CONTINUATION_HANDOFF_DE.md`.
