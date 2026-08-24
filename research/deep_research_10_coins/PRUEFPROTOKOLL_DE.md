# Verbindliches Protokoll fuer jeden neuen Pair-Versuch

Dieses Protokoll verhindert, dass zehn Coins mit einer globalen Regel
gleichgeschaltet oder bereits verworfene Laeufe wiederholt werden.

## 1. Baseline einfrieren

Vor einem neuen Versuch werden dokumentiert:

- Pair, Elternversion, Git-Commit, Strategiehash und Konfigurationshash;
- exakte Datenfenster, Datenmanifest und Zeitzone UTC;
- 1m-, 15m-, 1h- und 4h-Dateien samt Gap-/Duplikatpruefung;
- Basiskosten, Kostenstress, 250/80/3-Kapitalvertrag;
- aktuelles Einzelresultat und gemeinsamer V12.31-Beitrag;
- bereits ausgefuehrte Fingerprints aus research/executed_test_fingerprints.csv.

Ein frischer offizieller V12.31-Einzelbatch fuer 1/2/3 Jahre ist zuerst
nachzuholen. Aeltere V12.20-Zahlen werden als geerbte Vergleichsevidenz
gekennzeichnet, nicht umetikettiert.

## 2. Hypothese vorregistrieren

Pro Version genau ein Coin und eine grosse Entscheidungsaenderung. Vor dem
Finanzlauf festschreiben:

- kausale Marktannahme;
- genaue Entry-, Exit- und NO_TRADE-Regeln;
- Zeitrahmen und alle Parameter;
- ob genau ein Block oder Profit-Pyramiding erlaubt ist;
- erwartete Tradezahl und Fehlerbilder;
- Einzel-, Kosten-, Kurzfenster-, Drawdown- und Systemhuerden;
- welche Ergebnisse zum Verwerfen fuehren.

Eine Reservehypothese ist eine andere Familie und wird erst nach Abschluss der
primaeren Hypothese als neue Version registriert.

## 3. Auswahl ohne versteckten Holdout-Verbrauch

Das bekannte Drei-Jahres-Fenster ist nicht mehr unberuehrt. Deshalb:

1. feste Entwicklungsfalten und zeitlich spaetere Validierungsfalten;
2. rollende Walk-Forward-Fenster mit half-open Grenzen;
3. Parameterplateau statt eines einzelnen optimalen Punkts;
4. Zahl aller angesehenen Varianten im Trial Ledger;
5. PBO und Deflated Sharpe als Multiple-Testing-Diagnostik;
6. frische Paper-Forward-Daten als einzige wirklich neue Evidenz.

Ein Screen darf nur eine Hypothese auswaehlen. Er ist kein Ersatz fuer den
verriegelten Freqtrade-Lauf.

## 4. Exakter Einzeltest

Der einzelne Coin startet mit eigenen 250 USDT. Pflichtpruefungen:

- 1m Ausfuehrungsdetail und nur abgeschlossene Kerzen;
- 0,2 Prozent Gebuehr je Seite und 0,3 Prozent Kostenstress;
- 1-Bar-Lag-Stress;
- 1-, 2- und 3-Jahresansicht sowie Jahresfalten;
- Netto-PnL, Tradezahl, PF, Drawdown, Time-under-Water;
- MAE/MFE und PnL-Konzentration auf die groessten Gewinner;
- Entry-/Exit-Attribution und Haltedauer;
- Anzahl und Erwartungswert zusaetzlicher Bloecke;
- Lookahead-, Recursive- und Dateiaudit;
- Reproduzierbarkeit mit identischem Fingerprint.

Das Ziel +250 USDT darf nicht durch nachtraegliches Verschieben der Huerden
erzwungen werden.

## 5. Echter gemeinsamer Systemtest

Nur die getestete Coin-Route wird in eine neue, immutable Kopie von V12.31
eingesetzt. Alle anderen neun Routen bleiben exakt gleich. Alle zehn Coins
konkurrieren um ein einziges 250-USDT-Wallet und drei 80-USDT-Slots.

Vorab empfohlene Mindestbaseline:

- Gewinn groesser als +419,8571 USDT;
- Profit-Faktor mindestens 2,4358;
- geschlossener Drawdown hoechstens 12,5447 Prozent;
- kein bisher positives Paar wird negativ;
- der geaenderte Coin verbessert seinen gemeinsamen Beitrag;
- keine Sicherheits-, Kapital-, Datei- oder Kausalitaetsverletzung.

Wenn ein anderer Risiko-/Rendite-Trade-off zugelassen werden soll, muss er vor
dem Lauf schriftlich definiert werden. Nach Einsicht in das Ergebnis werden
die Huerden nicht gelockert.

## 6. Dauerhafter Datensatz je Coin

Jeder abgeschlossene Versuch erzeugt einen Datensatz mit:

- experiment_id, parent_experiment_id, Pair und Strategy-/Parameterhash;
- was seit dem direkten Vorgaenger exakt geaendert wurde und warum;
- Hypothese und vorab festgelegte Huerden;
- Datenfenster, Datenhash, Gebuehren und Laufzeit;
- Einzelresultate 1/2/3 Jahre und Kostenstress;
- gemeinsames Ergebnis sowie Pair- und Slot-Attribution;
- Entscheidung KEEP, REJECT oder TECHNICAL_ABORT;
- was funktioniert hat, was nicht und warum;
- verbindliche Nicht-wiederholen-Regel;
- genau naechster erlaubter Versuch.

Der Datensatz wird an die bestehende Pair-Historie, research/trial_ledger.csv
und research/executed_test_fingerprints.csv angehaengt. Ein identischer
Fingerprint wird nicht erneut ausgefuehrt.

## 7. Promotion

Ein historisch besserer Lauf ist nur Research-Evidenz. Danach folgen
deterministische Wiederholung, Shadow/Paper-Forward und manuelle Entscheidung.
Es gibt keine automatische Echtgeldfreigabe.
