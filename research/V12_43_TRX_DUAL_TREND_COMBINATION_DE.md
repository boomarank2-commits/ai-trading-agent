# V12.43 – Feste TRX-Dual-Trend-Kombination

Experiment: `V12.43-TRX-FIXED-DUAL-TREND-COMBINATION`

Elternstand: finanziell V12.33; zwei unveränderte TRX-Komponenten aus V12.33
und V12.42.

Vor dem ersten Ergebnis registrierter SHA-256:
`ff80b5d15a7135f76ef06974c80aab4b4722c15c31931533ec85bd58506dd8e3`

Status: **ABGELEHNT – ERSTE EXAKTE HÜRDE VERFEHLT.**

## Hypothese und feste Logik

V12.33-TRX war sehr selten, aber positiv: +15,234 USDT bei fünf Trades.
V12.42-TRX war deutlich aktiver und bestand alle Einzel-, jüngsten Jahres-
und Gebührenhürden, verfehlte aber im gemeinsamen Wallet den Profit-Faktor um
0,0202.

V12.43 kombiniert genau diese beiden unveränderten Entries:

1. den V12.33-TRX-Donchian-Core mit dessen Donchian-/Regime-Exit und frühem
   Failed-Breakout-Exit;
2. die V12.42-Supertrend(20,3)-Reserve über steigender EMA100 mit ihrem
   eigenen Supertrend-Shortflip-Exit.

Bei gleichzeitigem Signal hat der seltene Donchian-Core Vorrang. Exits werden
über den unveränderlichen `enter_tag` getrennt. TRX bleibt ein einzelner
80-USDT-Block und ist nicht für Pyramiding freigegeben. Alle anderen Paare,
Stopps, ROI, Protections, 250-USDT-/3×80-Vertrag und Dry-run bleiben V12.33.

## Strikte Vorab-Hürden

V12.43 muss die bereits betrachtete V12.42-Evidenz nicht nur erreichen,
sondern verbessern:

- TRX drei Jahre: mehr als +72,321 USDT, mindestens 42 Trades, PF mindestens
  2,44 und Drawdown höchstens 6,72 Prozent;
- jüngstes Jahr: mehr als +8,786 USDT und mindestens 11 Trades;
- 0,3-Prozent-Stress: mehr als +65,757 USDT und PF mindestens 2,23;
- gemeinsam: mehr als +449,7203 USDT, PF mindestens 2,4530, Drawdown höchstens
  8,3925 Prozent und jedes V12.33-positive Pair bleibt positiv;
- maximal drei Slots à 80 USDT und keine Verlustnachkäufe.

Scheitert die erste Hürde, werden alle späteren Läufe übersprungen und V12.33
wiederhergestellt. Es gibt keine Nachjustierung beider bereits angesehenen
Komponenten.

## Ergebnis

Der einmalige exakte Drei-Jahres-Lauf endete bei **+70,609 USDT**, 41 Trades,
Profit-Faktor **2,41** und geschlossenem Drawdown **6,75 Prozent**. Damit
verfehlte V12.43 alle vier strikten Verbesserungsgrenzen knapp:

- Gewinn nicht über +72,321 USDT;
- 41 statt mindestens 42 Trades;
- PF 2,41 statt mindestens 2,44;
- Drawdown 6,75 statt höchstens 6,72 Prozent.

2025 blieb mit −17,964 USDT und PF 0,39 negativ. Weil bereits die erste Hürde
scheiterte, wurden jüngstes Jahr, Gebührenstress und gemeinsames Wallet nicht
erneut ausgeführt. Der aktive Code wurde auf den exakten V12.33-Stand
zurückgestellt. Die V12.42-Einzelroute bleibt ein abgelehntes
Forschungsergebnis und wird nicht in den Paperbot übernommen.
