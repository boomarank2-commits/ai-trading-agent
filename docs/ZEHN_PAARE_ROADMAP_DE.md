# Zehn-Paare-Roadmap mit einem gemeinsamen 250-USDT-Wallet

Stand: 22.08.2026

Dieses Dokument ist die verbindliche Übergabe für die geplante Erweiterung auf
zehn Spot-Paare. Es beschreibt den erreichten Stand, die gewünschte
Kapitalverteilung, die getrennten Einzelpaar- und Portfoliotests und die
Reihenfolge der nächsten Arbeiten. Es ist keine Echtgeldfreigabe und kein
Gewinnversprechen.

## Bereits erreicht

Der aktive Paper-/Dry-run-Kandidat ist V12.15 mit dem exakten Strategy-Hash:

`3c5aaf823e16c1a2901c4861fcf6dbc21da4dd0f1314385d78be1f2de86c4a97`

V12.15 verwendet bereits sechs Paare:

1. BTC/USDT
2. ETH/USDT
3. SOL/USDT
4. XRP/USDT
5. BNB/USDT
6. DOGE/USDT

BTC, ETH und SOL bilden den ursprünglichen Kern. XRP, BNB und DOGE sind bereits
drei der gewünschten sieben Erweiterungen. Für das Ziel von insgesamt zehn
aktiven Paaren fehlen deshalb noch **vier** erfolgreich geprüfte Paare.

Der bestandene V12.15-Drei-Jahres-Portfoliolauf ergab bei einem gemeinsamen
250-USDT-Wallet:

| Kennzahl | V12.15 |
|---|---:|
| Endkapital | 545,409 USDT |
| Nettogewinn | +295,409 USDT |
| Trades | 122 |
| Profit Factor | 2,5554 |
| geschlossener Max-Drawdown | 8,19 % |
| Kapitalzeit | 23,07 % |
| Zeit vollständig ohne Position | 61,33 % |

Alle sechs Paare waren in diesem Lauf positiv. Das ist historische Simulation,
keine Garantie für zukünftige Ergebnisse.

Die bisherige Entwicklung ist vollständig im Trial Ledger und im
Fortsetzungsdokument erhalten. Kurzfassung:

- V8 bleibt als eingefrorene, reproduzierbare Research-Baseline erhalten.
- V12.9 kombinierte den Drei-Paare-Kern mit BTC-/ETH-Reclaim und
  Verlustcluster-Kontrolle.
- V12.10 und V12.11 prüften andere Continuation-/Regime-Ideen und wurden
  verworfen.
- V12.12 erweiterte den gemeinsamen Kern auf XRP, BNB und DOGE. Der finanzielle
  Befund war stark, aber der erste formale Dateiaudit war technisch ungültig.
- V12.13 entfernte den negativen ETH-Reclaim, verschlechterte jedoch das
  Gesamtportfolio durch veränderte Slot-/Protection-Chronologie und wurde
  verworfen.
- V12.14 sperrte Paare bereits nach dem ersten Verlust. Das reduzierte einzelne
  Verluste, verpasste aber gültige Folgetrends und wurde verworfen.
- V12.15 ergänzte nur einen späten Champion-Gewinnboden: nach mindestens +30 %
  laufendem Gewinn wird ein +5-%-Boden gesichert. Alle vorregistrierten Gates
  bestanden; dieser exakte Stand ist der aktive Paper-/Dry-run-Kandidat.
- V12.16 prüfte ADA als siebtes Paar und wurde trotz positiven ADA-Einzelbeitrags
  wegen schlechterer Gesamtportfolioqualität abgelehnt.
- Doppelte Backtest-Fingerabdrücke werden gesperrt; Annahmekriterien, gelesene
  Dateien, Prozesse und Ergebnisse bleiben dokumentiert.
- Alte benötigte Backtest-/Auditbelege bleiben erhalten, während Logs, Caches,
  temporäre Ausgaben und automatisch erzeugte Laufzeitdateien aus Git entfernt
  beziehungsweise in ignorierte Runtime-Verzeichnisse gelenkt wurden.

Die Detailquellen sind `research/trial_ledger.csv`,
`research/executed_test_fingerprints.csv` und
`research/CONTINUATION_HANDOFF_DE.md`.

V12.16 testete ADA/USDT als siebtes Paar. ADA selbst erzielte +27,809 USDT,
aber durch die gemeinsame Slot-Chronologie wurde SOL negativ, der bestehende
Sechs-Paare-Kern verlor Leistung und der Drawdown stieg auf 11,84 %. V12.16
wurde deshalb verworfen und V12.15 vollständig wiederhergestellt. Der identische
ADA-Fingerabdruck darf auf demselben Zeitraum nicht erneut laufen.

Zusätzlich wurden Replay- und Paritätsprüfungen verschärft. Ein Replay darf
nicht mehr eine aktuelle V12-Datei als eingefrorene V8-Evidenz ausgeben.
Strategie-, Konfigurations- und Risk-Policy-Hashes müssen zwischen Paper und
Replay zusammenpassen. Ein passender empirischer Paper-/Replay-Nachweis steht
noch aus und bleibt ein Pflicht-Gate vor neuen Strategiefamilien.

## Unveränderlicher Kapitalvertrag

Der normale Paperbot und der maßgebliche Gesamtportfolio-Backtest verwenden
auch mit zehn Paaren **kein zusätzliches Kapital**:

| Vertrag | Wert |
|---|---:|
| gemeinsames Start-Wallet | 250 USDT |
| Einsatz je Position/Slot | höchstens 80 USDT |
| gleichzeitig offene Slots | höchstens 3 |
| maximales Gesamtengagement | 240 USDT |
| freie Reserve | mindestens ungefähr 10 USDT vor weiteren Reserven/Kosten |
| Markt | Binance Spot |
| Richtung | long-only |
| Hebel/Margin/Futures | verboten |
| DCA/Martingale | deaktiviert |

Die zehn Paare erhalten **nicht jeweils 250 USDT im Gesamtportfolio**. Alle zehn
konkurrieren chronologisch um dieselben drei Slots. Es dürfen also gleichzeitig
zum Beispiel BTC, XRP und ein späteres zehntes Paar mit je 80 USDT offen sein.
Wenn nur ein gültiges Signal vorhanden ist, bleibt der Rest als Cash liegen;
Kapital wird nicht nur zur Erhöhung der Auslastung in einen schlechten Trade
gezwungen.

## Zwei verschiedene Testarten

### 1. Einzelpaar-Diagnose

Jedes der zehn Paare wird zusätzlich separat untersucht. Diese Läufe beantworten:

- erzeugt die exakt aktuelle Botlogik auf diesem Paar überhaupt Trades?
- sind Gewinn, Profit Factor, Drawdown, Verlustserien und Kosten tragbar?
- welche Entry-/Exit-Familie erzeugt Gewinn oder Verlust?
- wie sehen Kapitalzeit, Zeit ohne Position, MAE/MFE und Exit-Gründe aus?
- bleibt das Ergebnis unter höheren Kosten und zeitlich getrennten Fenstern stabil?

Jeder Einzelpaarlauf startet zur Vergleichbarkeit mit 250 virtuellen USDT und
behält 80 USDT je Position sowie maximal drei globale Slots in der Konfiguration.
Da der aktuelle Bot mehrere parallele Trades **desselben Paares** nicht erlaubt,
kann in einem reinen Einzelpaarlauf zurzeit höchstens eine Position gleichzeitig
offen sein. Die übrigen 170 USDT sind dann Reserve. Dieser Lauf ist eine
Attributions-/Qualitätsdiagnose und simuliert nicht zehn getrennte Live-Wallets.

Für jedes Paar werden mindestens folgende Fenster gespeichert:

- ein festes Ein-Jahres-Fenster für jüngeres Marktverhalten;
- ein festes Drei-Jahres-Fenster als Hauptdiagnose;
- Basiskosten 0,002 je Orderseite;
- ein vorab festgelegter höherer Kostenstress;
- exakt dieselbe Strategy-Datei, dieselben Parameter und derselbe Hash wie beim
  zugehörigen Portfolio-Kandidaten.

Bei zehn Paaren entstehen damit mindestens 20 sichtbare Einzelpaar-Zellen:
zehn Paare × ein Jahr und zehn Paare × drei Jahre. Ein Ergebnis darf nicht durch
Summieren dieser Einzeltests als Portfolioergebnis ausgegeben werden.

### 2. Gemeinsamer Zehn-Paare-Portfoliotest

Der entscheidende Test spielt alle zehn Paare in gemeinsamer chronologischer
Reihenfolge ab:

- genau ein gemeinsames 250-USDT-Wallet;
- höchstens drei offene 80-USDT-Positionen insgesamt;
- Gebühren, Stops, ROI, Custom Exits, Pair-Pausen und Protections wie im Bot;
- deterministische Reihenfolge bei gleichzeitigen Signalen;
- freier Slot wird nur durch ein tatsächlich gültiges Signal belegt;
- Verlust- und Protection-Zustände wirken auf dieselbe gemeinsame Historie;
- Ergebnis enthält auch verpasste Signale wegen belegter Slots.

Nur dieser Lauf zeigt, ob ein einzeln positives neues Paar das Gesamtportfolio
wirklich verbessert. V12.16/ADA hat bereits gezeigt, dass ein positives Paar
trotzdem schlechter sein kann, wenn es wertvollere BTC-, SOL- oder XRP-Signale
verdrängt.

## Wunsch: drei Slots im selben Paar

Der Wunsch, bei besonders guten Signalen notfalls alle drei 80-USDT-Slots im
selben Paar zu verwenden, ist hier ausdrücklich festgehalten. Er ist jedoch
**noch nicht Bestandteil von V12.15**.

Freqtrade führt in der aktuellen Konfiguration nur einen offenen Trade je Paar.
`position_adjustment_enable` ist aus Sicherheitsgründen deaktiviert; es gibt
kein DCA und kein Nachkaufen in Verlierer. Drei unabhängige Positionen desselben
Paares würden deshalb eine neue Portfolio-/Execution-Funktion benötigen.

Falls dieser Wunsch später umgesetzt wird, gilt er als eigener vorregistrierter
Challenger und nicht als kleine Konfigurationsänderung. Vor einer Übernahme muss
mindestens geprüft werden:

- drei getrennte, nachvollziehbare Einstiegssignale statt blindem Aufstocken;
- jede Teilposition höchstens 80 USDT und eigener Stop/Entry-Zeitpunkt;
- Gesamtengagement weiterhin höchstens 240 USDT;
- keine Umgehung des DCA-/Martingale-Verbots;
- Konzentrations- und Korrelationsrisiko gegenüber drei verschiedenen Paaren;
- gleicher Candle-Zeitpunkt darf nicht versehentlich dreifach dupliziert werden;
- Restart-, Order-, Stop- und Reconciliation-Verhalten mit mehreren
  Teilpositionen desselben Paares;
- separater Ein-/Drei-Jahres-, Kostenstress- und Gesamtportfoliotest.

Bis dieses Experiment bestanden ist, lautet der sichere produktive Vertrag:
**höchstens eine offene Position je Paar und höchstens drei verschiedene offene
Paare gleichzeitig.**

## Auswahl und Aufnahme der vier fehlenden Paare

Die vier noch fehlenden Paare sind noch nicht festgelegt. Sie werden nicht nach
einem bereits gesehenen Backtestergebnis ausgewählt. Vor dem ersten Test wird
für jeden Kandidaten dokumentiert:

- Experiment-ID und Kandidatenversion;
- Auswahlgrund, insbesondere ausreichende Spot-Liquidität und Datenhistorie;
- exaktes Paar und alle benötigten 1m-/15m-/1h-/4h-Datensätze;
- unveränderte oder bewusst neue Signalzuordnung;
- Strategy-, Config- und Datenhash;
- feste Ein-/Drei-Jahres-Zeiträume;
- feste Annahme- und Ablehnungskriterien;
- Kosten- und Lag-Stress;
- erwartete Zahl der Candle-Dateien;
- eindeutiger Fingerabdruck gegen doppelte Läufe.

Stablecoins gegeneinander, gehebelte Token, Futures/Perpetuals, sehr junge
Hype-Paare und Märkte mit unzureichender Historie werden nicht verwendet.

Die Erweiterung erfolgt schrittweise:

1. V12.15 mit sechs Paaren bleibt die unveränderte Referenz.
2. Ein siebter Kandidat wird vorregistriert und einzeln über ein und drei Jahre
   diagnostiziert.
3. Danach läuft genau ein gemeinsamer Sieben-Paare-Portfoliotest.
4. Nur bei bestandenen Gates wird der Kandidat übernommen.
5. Dasselbe Verfahren wird nacheinander für Paar acht, neun und zehn wiederholt.
6. Nach jeder Übernahme wird der neue Gesamtstand zum festen Vergleichsmaßstab.

Es werden nicht vier unbekannte Paare gleichzeitig ergänzt. Sonst wäre bei
einem besseren oder schlechteren Ergebnis nicht erkennbar, welches Paar die
Ursache war.

## Mindestinhalt jeder Entscheidung

Vor jedem Lauf werden die konkreten Zahlen festgeschrieben. Als Ausgangspunkt
dienen die V12.15-Werte; Grenzen dürfen nicht erst nach Sicht auf das Ergebnis
gelockert werden. Der Bericht muss mindestens enthalten:

- Endkapital und Nettogewinn nach Kosten;
- Tradezahl, Gewinne, Verluste und längste Verlustserie;
- Profit Factor;
- geschlossener und markierter Wallet-Drawdown;
- Kapitalzeit und Zeit vollständig ohne Position;
- Ergebnis jedes einzelnen Paares;
- Ergebnis des bisherigen Kernportfolios ohne den neuen Kandidaten;
- Entry-/Exit-Familien und Exit-Gründe;
- Slot-Verdrängung: welche Signale wegen drei belegter Slots ausfielen;
- Gebühren- und Stresskosten;
- Datenlücken, unerwartete Dateizugriffe und Kindprozesse;
- Development-/Validation-/Holdout- beziehungsweise Walk-Forward-Auswertung;
- PBO, Deflated Sharpe, Parameterplateau und PnL-Konzentration, sobald die
  erforderlichen vergleichbaren Return-Serien vorliegen;
- klare Entscheidung `ACCEPT`, `REJECT` oder `BLOCKED` mit Begründung.

Ein neues Paar wird nicht nur deshalb übernommen, weil sein Einzeltest positiv
ist oder die Gesamt-Endsumme geringfügig steigt. Profit Factor, Drawdown,
Kernschutz, Kostenstabilität und Slot-Verdrängung bleiben gleich wichtig.

## Parität zwischen Bot und Backtest

Der historische Test muss immer den zugehörigen Botstand spiegeln:

- exakt dieselbe Strategy-Quelldatei und derselbe Hash;
- dieselben Pair-Profile, Entry-/Exit-Regeln und Protections;
- dasselbe 250/80/3-Kapitalmodell;
- dieselben Stoploss-, ROI- und Custom-Stop-Regeln;
- Spot, long-only, kein Hebel und kein DCA;
- nur kausal verfügbare, geschlossene Candles;
- klarer Unterschied nur dort, wo der Einzelpaarlauf absichtlich seine
  Pair-Whitelist auf genau ein Diagnosepaar reduziert.

Eine zweite vereinfachte „Backteststrategie“ neben dem laufenden Bot ist
verboten. Jede Ergebnisdatei nennt Version, Hash, Zeitraum, Paare, Kosten,
Wallet, Stake, Slots und verwendete Candle-Dateien.

## Was als Nächstes passieren soll

1. V12.15 unverändert im Paper-/Dry-run belassen; keine Echtgeldfreigabe.
2. Einen frischen, hashgleichen Paper-Zeitraum sammeln und das offene
   Paper-/Replay-Paritäts-Gate schließen, ohne eine laufende Nutzerinstanz
   ungefragt anzufassen.
3. Full-History-, Fee-Stress-, Diagnose- und offene Walk-Forward-/PBO-/DSR-/
   Plateau-Gates abschließen.
4. Die Backtest-Oberfläche/den Runner auf eine dynamische Zehn-Paare-Matrix
   vorbereiten: je Paar ein und drei Jahre plus gemeinsames Portfolio.
5. Vier neue Kandidaten anhand vorab dokumentierter Liquiditäts-, Historien- und
   Sicherheitskriterien auswählen.
6. Kandidaten einzeln und nacheinander testen; nach jeder bestandenen Aufnahme
   den gemeinsamen Portfolio-Benchmark aktualisieren.
7. Erst nach zehn bestandenen Paaren einen finalen gemeinsamen Ein- und
   Drei-Jahres-Portfoliolauf mit 250 USDT, 3 × 80 USDT und allen zehn Paaren
   ausführen.
8. Den Wunsch nach bis zu drei Slots im selben Paar erst als separates
   Konzentrations-/Execution-Experiment bearbeiten; bis dahin bleibt eine
   Position je Paar die verbindliche Sicherheitsregel.

## Definition „fertig“

Das Zehn-Paare-Ziel ist erst erreicht, wenn:

- genau zehn namentlich festgelegte Spot-Paare in Strategy, Config, UI und
  Testmatrix übereinstimmen;
- für alle zehn vollständige Ein-/Drei-Jahres-Einzelberichte vorliegen;
- der gemeinsame Ein-/Drei-Jahres-Portfoliotest exakt 250 USDT, höchstens drei
  80-USDT-Slots und dieselbe aktive Botlogik verwendet;
- sämtliche Läufe eindeutig fingerprinted und im Trial Ledger dokumentiert sind;
- keine unerwarteten Daten-/Datei-/Prozesspfade verwendet wurden;
- die vorab festgelegten Portfolio-, Drawdown-, Kosten-, Kernschutz- und
  Statistik-Gates bestanden sind;
- der exakte bestandene Stand anschließend unverändert im Paper-/Dry-run läuft;
- eine manuelle Entscheidung vor jeder späteren Echtgeldfreigabe erfolgt.
