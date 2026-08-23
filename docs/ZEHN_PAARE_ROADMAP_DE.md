# V12.17 – Zehn-Paare-Paperbot und getrennte Backtest-Logik

Stand: 23.08.2026

Dieses Dokument ist die verbindliche technische Übergabe für den aktuellen
Zehn-Paare-Ausbau. Es ersetzt die frühere Annahme, dass die vier neuen Paare nur
in einer separaten Research-Strategie laufen oder dass der normale Sammel-
Backtest ein gemeinsames Portfolio simuliert.

Wichtig: **Paperbot und Einzel-Backtests sind zwei verschiedene Bausteine.**
Sie benutzen dieselbe Strategy-Logik, aber nicht dasselbe virtuelle Kapital-
experiment.

Es gibt weiterhin keine Echtgeldfreigabe und keine Gewinnzusage.

## 1. Historische Referenz

V12.15 bleibt als akzeptierte Sechs-Paare-Referenz erhalten. Der exakte frühere
Strategy-Hash lautet:

`3c5aaf823e16c1a2901c4861fcf6dbc21da4dd0f1314385d78be1f2de86c4a97`

V12.15 handelte:

1. BTC/USDT
2. ETH/USDT
3. SOL/USDT
4. XRP/USDT
5. BNB/USDT
6. DOGE/USDT

Der historische Drei-Jahres-Portfoliolauf von V12.15 startete mit einem
250-USDT-Wallet und ergab 545,409 USDT Endkapital, +295,409 USDT Nettogewinn,
122 Trades, Profit Factor 2,5554 und 8,19 % geschlossenen Max-Drawdown.
Diese Werte bleiben historische Evidenz und werden nicht als V12.17-Ergebnis
umetikettiert.

V12.16 testete ADA. ADA war isoliert positiv, verschlechterte aber durch
Slot-Verdrängung die gemeinsame Portfolioqualität. ADA bleibt deshalb für den
aktuellen Ausbau ausgeschlossen; der identische historische Versuch wird nicht
wiederholt.

## 2. Aktueller Paper-/Dry-run-Kandidat: V12.17

Die aktive Strategy bleibt unter demselben Freqtrade-Klassennamen und Pfad:

`runtime/user_data/strategies/CompressionBreakout250.py`

Die Strategy-Version ist jetzt `V12.17`.

Das aktive Paper-Universum besteht aus genau zehn Binance-Spot-Paaren:

1. BTC/USDT
2. ETH/USDT
3. SOL/USDT
4. XRP/USDT
5. BNB/USDT
6. DOGE/USDT
7. LINK/USDT
8. TRX/USDT
9. LTC/USDT
10. BCH/USDT

LINK, TRX, LTC und BCH wurden als langjährig etablierte, liquide Spot-Märkte mit
ausreichender Historie für Ein-/Zwei-/Drei-Jahres-Diagnosen gewählt. Sie starten
zunächst auf dem bereits existierenden Broad-Core-Donchian-Pfad. BTC und ETH
behalten ihre speziellen V12.15-Champion-/Reclaim-Wege. Die neuen vier Paare
werden erst nach ihren eigenen Backtests pair-spezifisch angepasst.

## 3. Kapitalvertrag des laufenden Paperbots

Der Paperbot besitzt **ein einziges gemeinsames virtuelles Wallet**:

| Vertrag | Wert |
|---|---:|
| gemeinsames Paper-Wallet | 250 USDT |
| Größe eines Entry-Blocks | maximal 80 USDT |
| maximale gebundene Summe | 240 USDT |
| gleichzeitig verfügbare Kapitalblöcke | maximal 3 |
| Markt | Binance Spot |
| Richtung | long-only |
| Hebel / Margin / Futures | verboten |
| Echtgeld | nicht freigegeben |

Die zehn Coins besitzen **keine getrennten Paper-Wallets**. Sie konkurrieren
live im Dry-run um dieselben drei 80-USDT-Blöcke.

Beispiele:

- BTC 80 + LINK 80 + SOL 80 = 240 USDT.
- LINK 80 + LINK später erneut 80 + XRP 80 = 240 USDT.
- BTC kann theoretisch drei 80-USDT-Blöcke halten, wenn drei zeitlich getrennte
  gültige Entry-Situationen auftreten und vorher kein anderer Coin die Blöcke
  belegt.

Sobald gebundenes Kapital frei wird, kann ein neues gültiges Signal eines
beliebigen der zehn Paare wieder einen 80-USDT-Block erhalten.

## 4. Mehrere 80er im selben Coin – aktueller technischer Stand

V12.17 aktiviert Freqtrades Position-Adjustment ausschließlich für den
Paper-/Backtest-Kandidaten:

- `position_adjustment_enable = true`
- `max_entry_position_adjustment = 2`
- damit maximal drei erfolgreiche Entries innerhalb eines offenen Pairs;
- jeder Zusatz-Entry bleibt auf höchstens 80 USDT begrenzt;
- die Summe aller offenen Stakes wird zusätzlich gegen 240 USDT geprüft.

Ein zweiter oder dritter 80er wird **nicht** allein deshalb gekauft, weil der
bestehende Trade im Minus liegt. Das wäre unerwünschtes blindes DCA/Martingale.

Ein Zusatzblock ist nur erlaubt, wenn:

1. derselbe Coin auf einer späteren Candle erneut ein normales gültiges
   `enter_long`-Signal erzeugt;
2. die Signalcandle zeitlich nach dem zuletzt gefüllten Entry liegt;
3. kein offener Entry-Orderkonflikt besteht;
4. noch weniger als drei erfolgreiche Entries in diesem Pair vorhanden sind;
5. der globale Exposure-Deckel von 240 USDT nach dem neuen 80er nicht
   überschritten wird;
6. Kill-Switch und übrige Sicherheitsregeln den Entry erlauben.

Freqtrade führt diese mehreren Entries derzeit innerhalb eines Freqtrade-Trades
mit mehreren Entry-Orders. Falls später jeder 80-USDT-Block einen vollständig
eigenen Trade-Lifecycle und eigenen unabhängigen Stop erhalten soll, ist das ein
separater Execution-Ausbau. Für den jetzigen Paper-Test reicht die
signal-gesteuerte Mehrfach-Entry-Logik aus, um das gewünschte Kapitalverhalten
zu messen.

## 5. Backtest – vollständig getrennt vom Paper-Wallet

Der normale Backtest beantwortet eine andere Frage:

> Wie hätte die **aktuelle V12.17-Strategy auf genau diesem einen Coin** über den
> gewählten historischen Zeitraum funktioniert, wenn dieser Coin ein eigenes
> virtuelles Startwallet von 250 USDT gehabt hätte?

Jeder Einzeltest startet deshalb neu mit:

- **250 USDT eigenem virtuellen Startwert**;
- derselben aktiven Strategy-Datei;
- derselben 80-USDT-Entry-Blockgröße;
- derselben Stop-/Exit-/Protection-Logik;
- denselben Binance-Spot-Candles;
- 1m Detaildaten und 15m/1h/4h Strategy-Daten;
- userseitig wählbaren **1, 2 oder 3 Jahren**.

Weil der Einzeltest den aktuellen Bot simuliert, darf auch ein einzelner Coin
bei späteren neuen gültigen Signalen innerhalb dieses einen Backtests einen
zweiten oder dritten 80er erhalten. Dadurch kann er in seiner eigenen
250-USDT-Simulation bis zu 240 USDT gleichzeitig binden.

Das bedeutet ausdrücklich **nicht**, dass der reale Paperbot jedem Coin 250 USDT
zuweist.

## 6. Button „Alle 10 nacheinander“

Die Backtest-UI enthält einen Sammelknopf:

`Alle 10 nacheinander`

Er übernimmt den gerade ausgewählten Zeitraum.

Beispiele:

- Auswahl `1 Jahr` → zehn getrennte Ein-Jahres-Backtests.
- Auswahl `2 Jahre` → zehn getrennte Zwei-Jahres-Backtests.
- Auswahl `3 Jahre` → zehn getrennte Drei-Jahres-Backtests.

Jeder der zehn Läufe beginnt erneut mit 250 USDT. Man kann daher nominell von
10 × 250 = 2.500 USDT Startwert über die zehn **unabhängigen Simulationen**
sprechen. Diese 2.500 USDT sind aber **kein gemeinsames Portfolio und keine
zusammenhängende Kapitalkurve**.

Die Einzelresultate dürfen nicht einfach zu einem Portfolioergebnis addiert
werden.

## 7. Späterer Gesamt-Systembacktest

Zusätzlich bleibt intern ein Portfolio-Backtestpfad erhalten. Dieser gehört
**nicht** zum normalen Coin-Dropdown und **nicht** zum Button „Alle 10
nacheinander“.

Dieser spätere finale Systemtest soll genau den Paperbot als Ganzes simulieren:

- ein gemeinsames 250-USDT-Wallet;
- zehn beobachtete Paare;
- maximal drei 80-USDT-Blöcke insgesamt;
- Zusatz-80er im selben Pair nur auf einem späteren neuen Signal;
- chronologische Konkurrenz aller Signale;
- echte Slot-/Kapital-Verdrängung;
- dieselben Gebühren, Stops, Exits und Protections.

Er beantwortet die Portfoliofrage. Die normalen Einzeltests beantworten dagegen
die Pair-Diagnosefrage. Diese beiden Ergebnisse dürfen nicht vermischt werden.

## 8. Strategie der vier neuen Paare

Die erste V12.17-Version optimiert LINK/TRX/LTC/BCH noch nicht auf bereits
angesehene Backtestergebnisse. Sie verwenden zunächst einen existierenden,
kausalen Broad-Core-Donchian-Pfad.

Das ist absichtlich konservativ. Der nächste Schritt ist nicht, wahllos
Parameter zu verändern, sondern zuerst für jeden Coin zu messen:

- Nettogewinn / Verlust;
- Profit Factor;
- Drawdown;
- Trefferquote;
- Zahl und Häufigkeit der Trades;
- größte Gewinner und Verlierer;
- Exit-Gründe;
- Champion-/Reclaim-/Broad-Core-Beitrag;
- Gebührenempfindlichkeit;
- Verlustserien;
- Kapitalnutzung;
- Verhalten bei einem zweiten/dritten signal-gesteuerten 80er.

Danach darf LINK anders parametriert werden als TRX, LTC oder BCH, wenn eine
vorregistrierte, kausal begründete Änderung nötig ist. Die bereits bewährten
BTC-/ETH-/SOL-/XRP-/BNB-/DOGE-Wege werden dabei nicht unnötig verändert.

## 9. UI und Charts

Die aktive `config.json` enthält alle zehn Paare in der statischen Binance-
Whitelist. Dadurch kennt der laufende Dry-run alle zehn Märkte; FreqUI kann deren
Marktdaten/Charts über denselben Binance-Spot-Datenpfad anzeigen.

Die repo-eigene Backtest-Oberfläche enthält ebenfalls alle zehn Paare als
Einzelauswahl:

- Bitcoin
- Ethereum
- Solana
- XRP
- BNB
- Dogecoin
- Chainlink
- TRON
- Litecoin
- Bitcoin Cash

Die Backtest-Oberfläche lädt für den ausgewählten Coin die benötigten Binance-
Candles bis zum aktuellen Stand nach und prüft Datenabdeckung, Lücken,
Duplikate sowie die tatsächlich gelesenen Candle-Dateien.

## 10. Sicherheitsgrenzen

V12.17 ist aktuell **Paper-/Dry-run only**.

Der Real-Money-Overlay wird absichtlich noch nicht auf die neue
Position-Adjustment-Logik promoviert. Dadurch kann V12.17 mit dem alten
Live-Overlay nicht unbemerkt als Echtgeldbot starten. Erst nach Paperbetrieb,
Einzeltests, Kosten-/Robustheitsprüfungen und finalem Systemtest darf über eine
separate Live-Promotion entschieden werden.

Weiterhin gelten:

- kein Short;
- kein Futures-/Margin-Handel;
- kein Hebel;
- kein blindes DCA/Martingale;
- pro Entry höchstens 80 USDT;
- insgesamt höchstens 240 USDT offen;
- lokaler Kill-Switch;
- pair-lokale Verlust-/Protection-Regeln;
- exakte Strategy-Quelle wird vor Start gehasht und gesperrt;
- Backtest-Dateizugriffe und Candle-Dateien werden auditiert;
- identische materielle Backtest-Fingerabdrücke werden nicht beliebig
  wiederholt.

## 11. Historische Research-Governance bleibt erhalten

V8 bleibt als eingefrorene Drei-Paare-Research-Baseline erhalten. Der alte
Replay wird nicht auf zehn Coins umgeschrieben. Er darf aber den heutigen
Zehn-Paare-Dry-run-Vertrag als aktuellen Runtime-Zustand erkennen, solange seine
historischen V8-Paare BTC/ETH/SOL darin weiterhin enthalten sind.

V12.15 bleibt als Sechs-Paare-Referenz dokumentiert. V12.16/ADA bleibt als
abgelehnter Versuch dokumentiert. Frühere verworfene Strategiefamilien wie
FAST_DONCHIAN_TREND, ORB_RETEST, ICHIMOKU_TREND und BOLLINGER_MR werden durch
V12.17 nicht wieder eingeführt.

## 12. Nächste Arbeitsreihenfolge

1. V12.17 technisch vollständig durch CI/Runtime-/Backtest-/Replay-Verträge
   bringen.
2. Paper-/Dry-run mit allen zehn Paaren starten und echte simulierte
   Entscheidungen/Entries aufzeichnen.
3. Für LINK, TRX, LTC und BCH zunächst unabhängige 1-/2-/3-Jahres-Diagnosen
   durchführen; bestehende Coins können mit derselben UI ebenfalls neu gemessen
   werden, sofern der Fingerprint einen materiell neuen V12.17-Test erlaubt.
4. Ergebnisse pro Pair bewerten und nur mit vorregistrierter Begründung
   pair-spezifisch anpassen.
5. Nach stabilen Einzelpaar-Ergebnissen den separaten finalen
   Zehn-Paare-Systembacktest mit einem gemeinsamen 250-USDT-Wallet und 3×80
   durchführen.
6. Paper-/Replay-/Execution-Parität und Kostenstress abschließen.
7. Erst danach über eine Echtgeld-Promotion oder spätere Erhöhung von Stake und
   Slotzahl entscheiden.

## 13. Was ausdrücklich nicht getan werden soll

- Einzelpair-Backtests zu einem künstlichen 2.500-USDT-Portfolio addieren.
- Den Sammelknopf „Alle 10“ als gemeinsamen Portfoliotest interpretieren.
- Jedem Coin im laufenden Paperbot 250 USDT geben.
- Zusatz-80er nur wegen fallender Kurse einsetzen.
- Bereits abgelehnte ADA-/Strategieexperimente identisch wiederholen.
- Die Echtgeld-Konfiguration automatisch mit der Paper-Konfiguration
  gleichsetzen.
- Die vier neuen Coins nachträglich auf dieselben historischen Daten so lange
  optimieren, bis irgendein gewünschter Gewinn erscheint.

Die maßgebliche Zielarchitektur lautet damit:

**Paperbot:** zehn Coins → ein gemeinsames 250-USDT-Wallet → maximal drei
80-USDT-Blöcke → dieselben oder verschiedene Coins je nach neuen gültigen
Signalen.

**Backtest:** ein ausgewählter Coin → eigenes 250-USDT-Testwallet → 1/2/3 Jahre;
„Alle 10“ → zehn solcher unabhängigen Läufe nacheinander.

**Späterer Systemtest:** alle zehn Coins gemeinsam → exakt das reale Paper-
Kapitalmodell 250 / 3×80.
