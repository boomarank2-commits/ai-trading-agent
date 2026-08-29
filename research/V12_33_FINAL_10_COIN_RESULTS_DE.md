# V12.33 – finale Zehn-Coin-Messung und gemeinsames 3×80-Portfolio

Stand: 25.08.2026

Strategie: `CompressionBreakout250` / `V12.33`

Exakter SHA-256:

`58d59413ef41b798c75c41bab0f98e377316ad3b289b6ba874876e841cdfb263`

Zeitraum: 25.08.2023 bis 24.08.2026, 1-Minuten-Detailkerzen,
15-Minuten-Strategiekerzen, Binance Spot/USDT, long-only, Gebühr 0,2 Prozent
je Orderseite, Protections aktiv und kein Backtest-Cache.

Status: **V12.33 bleibt Paper-/Dry-run-Kandidat; keine Echtgeldfreigabe und
keine Gewinngarantie.**

## Zehn voneinander getrennte Einzeltests

Jeder Coin startete in einem eigenen Lauf erneut mit 250 USDT. Diese zehn
Startwallets sind Diagnosekonten und bilden kein gemeinsames 2.500-USDT-
Portfolio.

| Coin | Gewinn | Endkapital | Trades | Profit-Faktor | Drawdown | Trefferquote |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BTC/USDT | +164,577 USDT | 414,577 USDT | 14 | 8,82 | 2,58 % | 21,43 % |
| ETH/USDT | +135,927 USDT | 385,927 USDT | 43 | 2,37 | 13,19 % | 9,30 % |
| SOL/USDT | +8,021 USDT | 258,021 USDT | 23 | 1,16 | 12,26 % | 21,74 % |
| XRP/USDT | +92,733 USDT | 342,733 USDT | 19 | 3,95 | 7,18 % | 21,05 % |
| BNB/USDT | +17,821 USDT | 267,821 USDT | 18 | 1,66 | 5,87 % | 27,78 % |
| DOGE/USDT | +112,552 USDT | 362,552 USDT | 25 | 2,90 | 6,45 % | 44,00 % |
| LINK/USDT | +60,835 USDT | 310,835 USDT | 30 | 1,61 | 26,02 % | 10,00 % |
| TRX/USDT | +15,234 USDT | 265,234 USDT | 5 | 2,53 | 3,63 % | 20,00 % |
| LTC/USDT | 0,000 USDT | 250,000 USDT | 0 | 0,00 | 0,00 % | 0,00 % |
| BCH/USDT | +25,398 USDT | 275,398 USDT | 20 | 1,54 | 11,21 % | 30,00 % |

Die rein diagnostische Summe beträgt +633,097 USDT bei 197 Trades. Sie darf
nicht als erreichbarer Gewinn eines einzigen 250-USDT-Wallets ausgegeben
werden, weil jeder Coin hier eigenes Startkapital hatte.

## Echter gemeinsamer Systemtest mit 250 USDT und 3×80

Alle zehn Märkte konkurrierten chronologisch um dasselbe 250-USDT-Wallet.
Höchstens drei Trades beziehungsweise 240 USDT konnten gleichzeitig gebunden
sein. Ein Platz wurde beim Fill belegt, blieb über die vollständige Laufzeit
des Trades blockiert und wurde erst nach dessen endgültigem Exit wieder frei.

| Kennzahl | Ergebnis |
| --- | ---: |
| Startkapital | 250,000 USDT |
| Endkapital | **671,915 USDT** |
| Gewinn | **+421,915 USDT** |
| Rendite | **+168,77 %** |
| Gewinn pro Kalendertag | +0,385 USDT |
| Trades | 154 |
| Profit-Faktor | 2,4530 |
| Trefferquote | 22,73 % |
| geschlossener Maximal-Drawdown | 12,1794 % |
| maximal gleichzeitig offene Trades | 3 |
| Konfigurationsgrenze | 3×80 USDT, höchstens 240 USDT |

### Beiträge im gemeinsamen Wallet

| Coin | Gewinnbeitrag | Trades |
| --- | ---: | ---: |
| DOGE/USDT | +113,206 USDT | 20 |
| XRP/USDT | +106,264 USDT | 12 |
| LINK/USDT | +84,713 USDT | 20 |
| BTC/USDT | +80,811 USDT | 12 |
| BNB/USDT | +33,139 USDT | 9 |
| BCH/USDT | +22,154 USDT | 19 |
| TRX/USDT | +12,352 USDT | 3 |
| ETH/USDT | +9,186 USDT | 38 |
| LTC/USDT | 0,000 USDT | 0 |
| SOL/USDT | −39,910 USDT | 21 |

Die Beiträge unterscheiden sich von den Einzeltests, weil offene Trades
knappe Plätze blockieren, Signale anderer Coins verdrängen und globale
Protections die spätere Chronologie verändern. Genau deshalb entscheidet der
gemeinsame Lauf über eine Bot-Promotion.

## Aus dem Deep-Research-Bericht geprüfte neue Wege

- `V12.34`: SOL Range-Reversion, −4,055 USDT, PF 0,44; verworfen.
- `V12.35`: technischer Datentypfehler vor Simulation; kein Finanzergebnis.
- `V12.36`: ungültiger Lauf, weil ein geerbter Donchian-Exit die neue Route
  sofort schloss; nicht finanziell interpretiert.
- `V12.37`: regelkonforme SOL-Supertrend-Reserve, +31,960 USDT und PF 2,36,
  aber nur zehn Trades statt der vorab verlangten zwölf; verworfen, nicht
  nachgestimmt.
- `V12.38`: SOL und LTC ohne Entry ergab gemeinsam +453,234 USDT und PF 2,75,
  machte jedoch ETH mit −1,662 USDT negativ; vorregistrierte Erhaltungshürde
  verletzt und deshalb verworfen.

Die aktive Quelle wurde nach diesen Versuchen bytegenau auf V12.33
zurückgesetzt. Neue SOL-Arbeit benötigt eine neue Vorregistrierung oder frische
Forward-Evidenz; die angesehenen Schwellen werden nicht nachträglich passend
gemacht.

## Offene Paritätsgrenze

Der Standard-Freqtrade-Backtest simuliert Strategie, Gebühren, Protections,
Slots und Positionslaufzeiten. Die zusätzliche laufende Tagesverlust-
Entry-Sperre des Paper-Supervisors ist im historischen Standardlauf weiterhin
nicht enthalten. Das Ergebnis ist deshalb ein genauer Strategie-/Portfolio-
Backtest, aber noch kein vollständiger Beweis jeder Supervisor-Entscheidung im
Paperbetrieb.
