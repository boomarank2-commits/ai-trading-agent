# Kausaler Routenscreen V2 – Abschluss offener Segmentpositionen

Stand: 24.08.2026

Der reine Forschungs-Screen `research/causal_pair_route_screen.py` hatte in
Schema V1 einen Randfehler: Er setzte eine am exakten Ende eines Jahressegments
noch offene Diagnoseposition zurück, bevor sie zum letzten im Segment
verfügbaren Schlusskurs bewertet wurde. Dadurch konnten einzelne Screen-
Kennzahlen zu hoch oder zu niedrig ausfallen.

Auswirkung:

- Kein aktiver Bot- oder Papertrade wurde davon ausgeführt.
- Die verriegelten Freqtrade-Backtests waren nicht betroffen.
- Alle aus V1 ausgewählten Kandidaten V12.23 bis V12.29 wurden ohnehin durch
  exakte Freqtrade-Läufe verworfen oder technisch abgebrochen; keiner wurde
  wegen des Screens freigegeben.
- Alte V1-JSON-Dateien bleiben nur als historische Diagnoseartefakte und dürfen
  nicht zur Auswahl eines neuen Kandidaten verwendet werden.

V2 behandelt das Zeitfenster explizit als `[Start, Ende)`, verarbeitet keine
Kerze am Endzeitpunkt und schließt eine noch offene Position zum letzten
Schlusskurs vor dem Ende. Die Schleife verwendet außerdem NumPy-Arrays statt
langsamer DataFrame-Einzelzugriffe. Ein Regressionstest deckt sowohl die
Endliquidation als auch die Exklusivität der Endkerze ab.

Ab jetzt muss jedes neue Screen-Ergebnis `schema_version: 2` und
`window_end_liquidation: true` enthalten. Vor einer Strategieübernahme bleiben
exakte Freqtrade-Einzel-, Kosten-, Kurzzeit- und gemeinsame Wallet-Tests
unverändert verpflichtend.
