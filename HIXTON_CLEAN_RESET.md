# HIXTON-V1 Clean-Reset

Dieser Branch ist ein isolierter Forschungszweig fuer einen frischen Hixton-Basistest. Er ersetzt die aktive V12.33 Entry-/Exit-Logik in diesem Branch durch genau eine gemeinsame Hixton-Familie und veraendert den bisherigen V12.33-Branch nicht.

## Zweck

Der Test soll ohne alte lokale Marktdaten, Backtest-Ergebnisse oder Dry-run-Datenbank aus einem neuen Ordner gestartet werden koennen. Ein frischer Clone enthaelt keine `runtime/user_data/data`- oder `runtime/user_data/backtest_results/hixton`-Historie. Diese Verzeichnisse entstehen erst lokal beim Test.

## Aktiver Hixton-Baseline-Vertrag

- Binance Spot, long-only
- 15m Strategie-Zeiteinheit
- geschlossene Kerzen fuer Signale
- VIDYA-Laenge 10
- Momentum-Laenge 20
- anschliessende SMA-Glaettung 15
- ATR-Laenge 200
- ATR-Multiplikator 2.0
- Long-Entry beim Cross des Schlusskurses ueber das obere Band
- Exit beim Cross des Schlusskurses unter das untere Band
- keine alten V12.33 Coin-Sonderrouten
- kein Pyramiding
- kein Real-Money-Betrieb; dieser Zweig ist Forschungs-/Dry-run-only

## Universum

BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, BNB/USDT, DOGE/USDT, LINK/USDT, TRX/USDT, LTC/USDT und BCH/USDT.

## Was der grosse Backtest-Knopf macht

`Alle 10 + 3x80 Portfolio testen` fuehrt bei einem neuen HIXTON-V1-Fingerprint nacheinander aus:

1. Fuer jeden der zehn Coins einen getrennten Backtest mit eigenem 250-USDT-Testwallet. Die Positionseinheit bleibt 80 USDT, damit die Messung zur spaeteren gemeinsamen Slot-Groesse passt.
2. Vor jedem echten neuen Lauf werden die benoetigten Binance-OHLCV-Daten fuer 1m, 15m, 1h und 4h bis zum aktuellen Stand angefordert. Der Download beginnt zusaetzlich 75 Tage vor dem eigentlichen Testfenster als Warm-up.
3. Candle-Integritaet wird auf fehlende Bereiche, Duplikate, falsche Reihenfolge, zu spaeten Start und veraltetes Ende geprueft. Bei einem defekten Coin werden dessen vier lokalen Candle-Dateien geloescht, komplett neu von Binance geladen und erneut geprueft.
4. Der Backtest nutzt 1m Detaildaten, 0.2 Prozent Gebuehr je Orderseite, keinen Backtest-Cache und prueft anschliessend die tatsaechliche Zeitabdeckung.
5. Erst wenn alle zehn Einzeltests gueltig abgeschlossen sind, startet automatisch der gemeinsame chronologische Portfolio-Backtest: ein gemeinsames 250-USDT-Wallet, maximal drei gleichzeitige Positionen zu je 80 USDT, maximal 240 USDT Exposition.
6. Die zehn Einzel-P/L-Werte werden niemals als gemeinsames Portfolioergebnis addiert. Das Portfolioergebnis stammt ausschliesslich aus dem chronologischen gemeinsamen Lauf.

## Forschungs- und Duplicate-Regel

HIXTON-V1 besitzt ein eigenes Versuchsregister (`research/hixton_trial_ledger.csv`) und ein eigenes Ausfuehrungsregister. Ein exakt bereits getesteter Strategie-/Konfigurations-/Pair-/Zeitraum-Fingerprint wird nicht als neues Experiment erneut ausgefuehrt. Eine spaetere Hixton-Variante muss eine materiell andere Logik oder Parameterkombination besitzen und als neues Experiment registriert werden.

Das verhindert, dass bekannte Strategie A spaeter nur unter anderem Namen noch einmal als angeblich neuer Test A ausgefuehrt wird.

## Ergebnisanzeige

Die UI zeigt die zehn Einzelresultate getrennt sowie anschliessend das gemeinsame 3x80-Portfolio. Fuer das Portfolio werden unter anderem Gewinn, Endkapital, Trades, Profit Factor, Drawdown, durchschnittlicher Gewinn je Kalendertag, maximale gleichzeitige Positionen, maximale Kapitalbindung und Pair-Beitraege angezeigt.

Die langfristige Entwicklungsmarke von 2.40 USDT je Kalendertag fuer das gesamte gemeinsame 3x80-System wird nur als Vergleichswert angezeigt. Sie ist keine Gewinnzusage und kein Grund, ein historisches Fenster nachtraeglich darauf zu ueberfitten.

## Branch

`agent/hixton-clean-reset`

Fuer einen wirklich frischen Versuch diesen Branch in einen neuen leeren Ordner klonen und dort `STARTBOT.bat` verwenden. Anschliessend in FreqUI den Bereich `Backtest` oeffnen, 3 Jahre ausgewaehlt lassen und `Alle 10 + 3x80 Portfolio testen` starten.
