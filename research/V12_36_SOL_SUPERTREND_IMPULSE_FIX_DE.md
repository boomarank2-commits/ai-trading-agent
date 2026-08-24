# V12.36 – technische Ausführung der SOL-Supertrend-Reserve

Stand: 25.08.2026

Experiment: `V12.36-SOL-ATR-SUPERTREND-IMPULSE-BOOL-FIX`

Elternstand: `V12.35-SOL-ATR-SUPERTREND-IMPULSE`

Finanzieller Elternstand: `V12.33-LTC-NO-TRADE-COUNTERFACTUAL`

Strategie: `CompressionBreakout250`, Version `V12.36`

Vor dem ersten V12.36-Finanzlauf registrierter SHA-256:

`d50e84dbc49689ad41346c8350b3a19512b26930340f1bf5dbd3dfcdbcf41724`

Status: **UNGÜLTIGER LAUF – IMPLEMENTIERUNG ENTSPRACH NICHT DER VORREGEL.**

## Ausschließlich technische Korrektur

V12.35 erzeugte kein Finanzergebnis. Pandas lieferte die rollierenden
Vier-Kerzen-Markierungen als Float-Serie; die Verknüpfung mit booleschen
Serien stoppte vor der Simulation. V12.36 wandelt ausschließlich diese zwei
Markierungen explizit mit `.astype(bool)` um und aktualisiert Versions-Tags.

Sämtliche Handelsregeln und Hürden sind identisch zu V12.35: 4h-Supertrend
(14, 3,5), Makrotrend über steigender EMA200, ADX mindestens 20,
30-Tage-Momentum mindestens 5 Prozent, erstes gültiges 15m-Signal innerhalb
einer Stunde, RSI 50–72, ein Block und Exit beim Shortflip. V12.34 ist nicht
enthalten. LTC bleibt ohne Einstieg; alle übrigen Routen bleiben V12.33.

## Unveränderte bindende Hürden

1. SOL drei Jahre: mindestens +20 USDT, zwölf Trades, PF über 1,30 und
   Drawdown höchstens 12 Prozent.
2. SOL jüngstes Jahr: mindestens drei Trades und positiv.
3. SOL bei 0,3 Prozent Gebühr je Seite: mindestens +10 USDT und PF über 1,20.
4. Gemeinsam: Gewinn über +421,9152 USDT, PF mindestens 2,4530, Drawdown
   höchstens 12,1794 Prozent, SOL positiv und alle anderen positiven Paare
   weiter positiv.
5. Maximal drei belegte 80-USDT-Plätze; Freigabe eines Platzes erst nach dem
   endgültigen Trade-Exit; sämtliche Sicherheitsverträge bleiben grün.

Keine Schwelle darf nach dem ersten Finanzergebnis verändert werden. Keine
Echtgeldfreigabe oder Gewinngarantie.

## Ergebnis und Auditfund

Der Runner erzeugte zehn Trades und −3,198 USDT, dieses Ergebnis ist jedoch
kein Test der registrierten Supertrend-Hypothese. Alle zehn Trades wurden in
derselben Kerze durch den aus V12.31 geerbten
`v12_17_sol_failed_breakout`-Callback geschlossen. Die vorregistrierte Route
verlangte dagegen ausdrücklich Exit nur per Supertrend-Shortflip,
unverändertem Hard-Stop, ROI oder Protections.

Der Auditfund ist vor jeder Ergebnisinterpretation bindend. V12.36 wird als
`ABORT_IMPLEMENTATION_MISMATCH` geführt, nicht als finanzieller Reject. Eine
neue V12.37 darf ausschließlich den alten Donchian-Custom-Exit für den neuen
SOL-Supertrend-Tag umgehen. Schwellen und Hürden bleiben identisch.
