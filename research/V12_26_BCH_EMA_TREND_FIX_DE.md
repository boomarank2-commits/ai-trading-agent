# V12.26 – technische 4h-Korrektur der BCH-V12.25-Hypothese

Stand: 24.08.2026

Experiment: `V12.26-BCH-EMA30-80-MACRO100-FIX`

Elternstand: `V12.25-BCH-EMA30-80-MACRO100` (vor Simulation abgebrochen)

Strategie: `CompressionBreakout250`, Version `V12.26`

Vor dem ersten Finanzlauf registrierter SHA-256:

`ba7752f8b03600cb244bab6b291e7200d56f6d6e14620ede6f6edd6443b10634`

Status: **VERWORFEN – PROFITABEL, ABER RISIKOHÜRDE VERFEHLT.**

V12.25 erreichte keine Simulation und lieferte keine Finanzkennzahl. V12.26
ändert ausschließlich die fehlerhafte Verdrahtung: `bch_ema_fast`,
`bch_ema_slow` und `bch_ema_macro` werden im 4h- statt im 1h-Decorator
berechnet. Schwellen, Entry, Exit, Stop, Gebühren, Kapital und alle anderen
Pair-Regeln bleiben identisch zur vorregistrierten V12.25-Hypothese.

Es gelten unverändert sämtliche Entscheidungshürden aus
`V12_25_BCH_EMA_TREND_DE.md`: BCH 3y positiv mit mindestens 15 Trades, PF über
1,0, DD unter 12,52 Prozent und mindestens 35 USDT Verbesserung; positives
letztes Jahr; positiver Kostenstress; gemeinsamer Gewinn über +280,7752 USDT,
PF mindestens 2,0230, DD höchstens 16,07 Prozent, kein positives Paar kippt und
alle Sicherheitsverträge bleiben grün.

## Exakte Ergebnisse nach der Vorregistrierung

Alle isolierten BCH-Hürden wurden bestanden:

| BCH-Einzeltest | Ergebnis |
| --- | ---: |
| 3 Jahre, 0,2 % Gebühr je Seite | +25,398 USDT; 20 Trades; PF 1,54; DD 11,21 % |
| letztes Jahr, 0,2 % Gebühr je Seite | +3,012 USDT; 8 Trades; PF 1,16; DD 7,66 % |
| 3 Jahre, 0,3 % Gebühr je Seite | +22,426 USDT; 20 Trades; PF 1,45; DD 11,75 % |

Gegenüber V12.22 BCH −24,25 USDT war der normale Dreijahreslauf um rund
49,65 USDT besser. Ein 50-Prozent-Gewinner lieferte jedoch 39,90 USDT und damit
mehr als den gesamten Nettogewinn; die Evidenz bleibt konzentriert.

Im gemeinsamen 250-USDT-Wallet ergaben sich:

| Kennzahl | V12.22 | V12.26 | Änderung |
| --- | ---: | ---: | ---: |
| Gewinn | +280,775 USDT | +317,451 USDT | +36,676 USDT |
| Trades | 136 | 146 | +10 |
| Profit-Faktor | 2,0230 | 2,0892 | +0,0662 |
| geschlossener Drawdown | 16,07 % | 16,47 % | +0,40 Punkte |
| BCH-Beitrag | −4,305 USDT | +22,154 USDT | +26,459 USDT |

Kein zuvor positives Paar wurde negativ. Die vorab bindende Drawdown-Hürde
scheiterte aber bei 16,4717 statt höchstens 16,07 Prozent. Sie wird nach Sicht
auf das Ergebnis nicht aufgeweicht. Entscheidung: `REJECT_DO_NOT_PROMOTE`.
Der aktive Paper-Quelltext wird exakt auf V12.22 zurückgesetzt. Die profitable
BCH-Route bleibt als dokumentierter, nicht aktiver Challenger erhalten.
