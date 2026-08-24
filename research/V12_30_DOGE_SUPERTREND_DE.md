# V12.30 – DOGE Supertrend20×3 oberhalb steigender EMA100

Stand: 24.08.2026

Experiment: `V12.30-DOGE-SUPERTREND20X3-MACRO100`

Elternstand: `V12.22-SOL-ADX21` (aktive Vergleichsbasis)

Strategie: `CompressionBreakout250`, Version `V12.30`

Vor dem ersten Finanzlauf registrierter SHA-256:

`978c4626ba213de9bf8b93acceaf209074ab41b9d31a5a62da893e3018925630`

Status: **ÜBERNOMMEN ALS AKTIVER PAPER-/DRY-RUN-KANDIDAT.**

## Auswahl ohne V1-Randfehler

Dies ist die erste Auswahl mit dem reparierten kausalen Screen Schema V2.
Offene Positionen werden am Segmentende zum letzten zulässigen Schlusskurs
bewertet; die Endkerze selbst bleibt ausgeschlossen. Das Ergebnis enthält
`schema_version: 2` und `window_end_liquidation: true`.

Von 186 festen einfachen Routen bestanden 35 beide Entwicklungsjahre, das
unberührte dritte Jahr und den 0,3-Prozent-Kostenstress. Die vorab programmierte
Rangfolge nach dem schwächsten Jahresgewinn wählte:

- 4h-Supertrend, ATR-Periode 20, Multiplikator 3,0,
- Long-Einstieg nur beim Richtungswechsel von nicht-long auf long,
- DOGE-Kurs über EMA100 und EMA100 höher als zwölf 4h-Kerzen zuvor,
- Exit beim Supertrend-Wechsel von long auf short,
- harter Stop unverändert -5,5 Prozent,
- genau ein 80-USDT-Block; DOGE erhält kein Pyramiding.

Screen-Ergebnis je Jahr: +26,5544 / +137,6245 / +22,8415 USDT bei 10 / 8 / 7
Trades. Kostenstress: +182,6508 USDT, 25 Trades, PF 3,9850 und 7,7636 Prozent
Drawdown. Der Screen ist nur Hypothesenauswahl, keine Bot-Bestätigung.

## Genau eine Strategieänderung

Nur DOGE ersetzt seine V12.22-Entry-/Exit-Route. Die übrigen neun Coins,
SOL-ADX21, 250-USDT-Wallet, maximal drei 80-USDT-Plätze, Spot long-only, 1x,
Stop-/Schutzregeln, Dry-run und Backtest-Parität bleiben unverändert.

## Vorab bindende Hürden

1. DOGE drei Jahre: mindestens 20 Trades, mindestens +100 USDT, PF über 2,0,
   geschlossener Drawdown höchstens 12 Prozent, durchschnittlicher Einsatz
   höchstens 80,01 USDT und keine Zusatzblöcke.
2. Jüngstes Jahr: mindestens fünf Trades und mindestens +10 USDT.
3. 0,3-Prozent-Kostenstress: mindestens +80 USDT und PF über 2,0.
4. Gemeinsames Wallet: Gewinn über +280,7752 USDT, PF mindestens 2,0230,
   Drawdown höchstens 16,07 Prozent und kein positives V12.22-Paar wird
   negativ.
5. Alle Strategie-, Kausalitäts-, Kapital-, Dry-run- und Sicherheitstests grün.

Nach Beginn des ersten exakten Laufs bleiben Route, Hash und Gates unverändert.
Scheitert eine Hürde, wird V12.30 verworfen und V12.22 bytegenau reaktiviert.

## Exakte Ergebnisse

- DOGE, drei Jahre, 0,2 Prozent Gebühr: **+112,552 USDT**, 25 Trades,
  PF 2,90, geschlossener Drawdown 6,45 Prozent, durchschnittlicher Einsatz
  79,922 USDT und keine Zusatzblöcke.
- DOGE, jüngstes Jahr: **+22,850 USDT**, 7 Trades, geschlossener Drawdown
  4,82 Prozent.
- DOGE, drei Jahre, 0,3 Prozent Gebühr: **+108,919 USDT**, 25 Trades,
  PF 2,7775 und geschlossener Drawdown 6,68 Prozent.
- Gemeinsames Zehn-Coin-Wallet: Start 250, Ende **623,606 USDT**, Gewinn
  **+373,6057 USDT**, 145 Trades, PF 2,3576 und geschlossener Drawdown
  13,3897 Prozent.

Gemeinsame Paarbeiträge: BTC +115,537; LINK +90,925; DOGE +80,635; XRP
+70,536; BNB +36,024; ETH +23,660; TRX +12,352; BCH -2,700; LTC -24,644;
SOL -28,719 USDT. Alle in V12.22 positiven Paare blieben positiv.

Gegenüber V12.22 steigt der gemeinsame Gewinn um **+92,8305 USDT**, der PF
von 2,0230 auf 2,3576; der geschlossene Drawdown sinkt von 16,07 auf 13,3897
Prozent. Alle vorab bindenden Hürden bestanden.

Entscheidung: `KEEP_AS_ACTIVE_PAPER_CHALLENGER_NOT_REAL_MONEY`. V12.30 ist
damit die gemeinsame Quelle für Paperbot und künftige Backtests. Das ist keine
Echtgeldfreigabe und kein Versprechen, dass ein zukünftiger Zeitraum oder jeder
einzelne Coin 250 USDT Gewinn erzielt.
