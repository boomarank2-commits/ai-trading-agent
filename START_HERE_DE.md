# Start hier: V12.20-Zehn-Paare-Testbot und Research-System

Stand: 24.08.2026

## Aktueller Stand

Die eingefrorene historische Research-Baseline bleibt `CompressionBreakout250` /
V8 unter `research/baselines/V8/`.

Der aktuelle Paper-/Dry-run-Kandidat ist jedoch
`runtime/user_data/strategies/CompressionBreakout250.py` / **V12.20** auf dem
Arbeitsbranch `agent/v12-17-ten-pair-research-ui`.

V12.20 läuft ausschließlich mit virtuellem Geld und beobachtet zehn Binance-
Spot-Paare:

- BTC/USDT
- ETH/USDT
- SOL/USDT
- XRP/USDT
- BNB/USDT
- DOGE/USDT
- LINK/USDT
- TRX/USDT
- LTC/USDT
- BCH/USDT

Der Paperbot besitzt **ein einziges gemeinsames 250-USDT-Wallet**. Ein Entry-
Block ist maximal 80 USDT groß. Insgesamt dürfen höchstens 240 USDT bzw. drei
80-USDT-Blöcke gleichzeitig gebunden sein.

BTC, ETH, LINK und TRX dürfen in einem bereits offenen Trade einen zweiten oder
dritten 80-USDT-Block erhalten, aber nur wenn auf einer späteren Candle erneut
ein vollständiges normales Entry-Signal entsteht, der Trade im Gewinn liegt
und der neue Preis über allen früheren Entry-Fills liegt. Die anderen sechs
Coins behalten normale erste Entries, aber keine Zusatzblöcke. Verlust-Nachkauf
und Martingale sind gesperrt.

Status:

**V12.20 PAPER-/DRY-RUN-KANDIDAT – NICHT FÜR ECHTGELD FREIGEGEBEN.**

Der Live-Overlay bleibt absichtlich noch auf dem alten, nicht promovierten
Position-Adjustment-Vertrag. Dadurch darf V12.20 nicht versehentlich als
Echtgeldbot starten.

## Wichtige historische Referenzen

V12.15 bleibt die akzeptierte Sechs-Paare-Referenz vor dem Zehner-Ausbau. Der
historische Drei-Jahres-Portfoliolauf von V12.15 startete mit 250 USDT und
lieferte 545,409 USDT Endkapital, +295,409 USDT Nettogewinn, 122 Trades, Profit
Factor 2,5554 und 8,19 % geschlossenen Max-Drawdown.

V12.16 testete ADA. ADA war einzeln positiv, verschlechterte aber die gemeinsame
Portfolioqualität durch Slot-Verdrängung und wurde verworfen. ADA gehört deshalb
nicht zum aktuellen Zehner-Universum.

Die ausführliche Historie bleibt in:

- `research/CONTINUATION_HANDOFF_DE.md`
- `research/trial_ledger.csv`
- `research/executed_test_fingerprints.csv`
- den einzelnen V12.xx-Research-Dokumenten.

Die aktuelle V12.18-Reparaturübergabe steht in:

`research/V12_18_REPAIR_HANDOFF_DE.md`

Die darauf aufbauende V12.19-Laufzeit-/Lernübergabe steht in:

`research/V12_19_PERSISTENT_PAIR_LEARNING_DE.md`

Die aktuelle finanzielle V12.20-Entscheidung und der genaue nächste Zyklus
stehen in:

`research/V12_20_SELECTIVE_PYRAMID_DE.md`

Die frühere V12.17-Roadmap bleibt als historische Fehler- und Herkunftsakte
unter `research/V12_17_CONTINUATION_HANDOFF_DE.md` erhalten.

Die ursprüngliche, inzwischen ausdrücklich als historisch markierte
V12.17-Zehn-Paare-Roadmap steht in:

`docs/ZEHN_PAARE_ROADMAP_DE.md`

## Die zwei Kapitalmodelle nicht verwechseln

### 1. Laufender Paperbot

Ein gemeinsames Wallet:

```text
250 USDT gesamt
→ maximal 3 Kapitalblöcke
→ maximal 80 USDT je Block
→ maximal 240 USDT gleichzeitig investiert
→ zehn Coins konkurrieren um dieselben Blöcke
```

Beispiele:

```text
BTC 80 + LINK 80 + SOL 80
LINK 80 + LINK später erneut 80 + XRP 80
BTC 80 + BTC später 80 + BTC später 80
```

Voraussetzung für einen weiteren Block im selben Coin sind ein neues gültiges
Signal auf einer späteren Candle, ein bereits profitabler Trade, ein Kurs über
allen früheren Fills und freie globale Exposure.

### 2. Normaler Einzelpair-Backtest

Der Backtest ist davon getrennt. Ein ausgewählter Coin bekommt für seine
historische Simulation **ein eigenes 250-USDT-Startwallet**.

Die UI bietet:

- 1 Jahr
- 2 Jahre
- 3 Jahre

`Gewählten Coin testen` testet genau den ausgewählten Coin.

`Alle 10 einzeln testen` nimmt den aktuell gewählten Zeitraum und startet
automatisch zehn unabhängige Läufe nacheinander. Jeder Coin beginnt erneut mit
250 USDT. Du musst den Startknopf daher nicht zehnmal drücken.

V12.20 speichert diesen Zehner-Batch nach jedem Coin. Die Warteschlange gehört
zum lokalen Bot-Server und nicht zur gerade sichtbaren Browserseite: Du kannst
zwischen Trade, Dashboard, Chart, Logs und Backtest wechseln, ohne den Batch zu
stoppen. Nach einem Bot-Neustart wird ein unvollständiger Batch als fortsetzbar
erkannt; bereits vollständig erhaltene identische Tests werden nicht erneut
simuliert.

Damit sind bei zehn Einzeltests nominell 10 × 250 = 2.500 USDT Startwerte im
Spiel, aber **nicht als gemeinsames Portfolio**. Die Ergebnisse dürfen nicht
addiert und als gemeinsame Kapitalkurve interpretiert werden.

Der gemeinsame Zehn-Paare-Systembacktest bleibt für Replay und Audit intern
erhalten. Er ist bewusst kein dritter Knopf im normalen Backtest-Bildschirm.

## Neue Paare und erste Strategiezuordnung

LINK, TRX, LTC und BCH starten in V12.20 weiterhin auf dem bereits vorhandenen
Broad-Core-Donchian-Pfad, den auch SOL/XRP/BNB/DOGE verwenden.

BTC und ETH behalten ihre spezialisierten Champion-/Reclaim-Pfade aus dem
bewährten V12.15-Kern.

Die vier neuen Coins werden nicht sofort auf bereits angesehene Historie
überoptimiert. Zuerst werden ihre unabhängigen Backtests gemessen. Danach dürfen
pair-spezifische Parameter oder Signalpfade einzeln, vorregistriert und mit
klarer Begründung angepasst werden.

## Selektive weitere Entries im selben Pair

V12.20 verwendet technisch für den Paper-/Backtest-Kandidaten:

```text
position_adjustment_enable = true
max_entry_position_adjustment = 2
```

Dadurch kann ein offener Freqtrade-Trade bei BTC, ETH, LINK und TRX bis zu drei
erfolgreiche Entry-Orders enthalten. Für SOL, XRP, BNB, DOGE, LTC und BCH gibt
`adjust_trade_position()` immer `None` zurück; diese Coins dürfen aber weiterhin
ihren normalen ersten Trade eröffnen.

Zusätzliche Sicherheitslogik prüft:

- neues `enter_long`-Signal vorhanden;
- Signalcandle liegt nach dem letzten gefüllten Entry;
- offener Trade ist bereits profitabel;
- neuer Entry-Kurs liegt strikt über allen vorherigen Entry-Fills;
- kein offener Entry-Orderkonflikt;
- weniger als drei erfolgreiche Entries im Pair;
- Kill-Switch nicht aktiv;
- globale offene Stake + 80 <= 240 USDT.

Wichtig: Zusätzliche Freqtrade-Entry-Orders innerhalb eines bereits offenen
Trades zählen nicht als zusätzliche `max_open_trades`. Deshalb wird die globale
Stake-Summe zusätzlich separat begrenzt.

## Testbot starten

Für den 24/7-Paper-Test:

```bat
STARTBOT.bat
```

Startpfad:

```text
STARTBOT.bat
→ runtime/scripts/run-testbot-supervised.ps1
→ runtime/scripts/start-testbot-24x7.ps1
→ locked_freqtrade.py
→ config.json + CompressionBreakout250.py
```

Die Strategy-Quelle wird vor dem Start gehasht und während der Sitzung gegen
unerwartete Änderungen geschützt. Die wirksame Freqtrade-Konfiguration wird
vor dem Start mit `runtime/validate_dryrun_config.py` gegen den exakten
250/80/3-/Zehn-Paare-Vertrag geprüft.

Der sichtbare STARTBOT-Prozess bleibt Teil des Sicherheitsvertrags. Die
Bedienung steht in `TESTBOT_ANLEITUNG.md`.

## FreqUI und Charts

Die aktive `runtime/user_data/config.json` enthält alle zehn Paare in der
statischen Binance-Whitelist. Damit kennt der laufende Freqtrade-Dry-run alle
zehn Märkte und kann deren Marktdaten/Charts über den normalen FreqUI-/Binance-
Datenpfad bereitstellen.

Zusätzlich wird in FreqUI die repo-eigene Backtest-Seite eingeblendet. Sie
enthält alle zehn Coins als Auswahl und startet die gesperrten historischen
Backtests.

## Historischer Backtest

Die aktive Backtest-Kette verwendet dieselbe Strategy-Datei wie STARTBOT. Es
existiert keine zweite vereinfachte Backteststrategie.

Für einen Einzeltest:

1. Coin auswählen.
2. 1, 2 oder 3 Jahre auswählen.
3. `Gewählten Coin testen` drücken.
4. Der Runner lädt/ergänzt die benötigten Binance-Daten.
5. Der Lauf startet mit 250 USDT eigenem virtuellem Wallet.
6. Strategy-/Config-/Candle-Dateien werden auditiert.
7. Das Resultat zeigt unter anderem P/L, USDT/Tag, Profit Factor, Drawdown,
   Trefferquote, Tradezahl, tatsächliche Entry-Blöcke sowie Paar-/Entry-/Exit-
   Attribution.
8. Plan, Zeitanteile und Vergleich zum vorherigen materiell anderen Lauf
   werden im Ergebnis und in der pair-spezifischen Lernakte gespeichert.

Für alle zehn getrennten Coin-Tests:

`Alle 10 einzeln testen`

Dieser Knopf startet zehn unabhängige 250-USDT-Testwallets nacheinander. Die
Ergebnisse bleiben je Coin getrennt. Der interne `PORTFOLIO`-Pfad für zehn Coins
mit einem gemeinsamen 250-USDT-Wallet bleibt ausschließlich für Replay/Audit
erhalten und wird nicht als dritter UI-Knopf angeboten.

Für lokale historische Werkzeuge existiert zusätzlich:

```bat
HISTORISCHER_BACKTEST.bat
```

## Historischer V8-Full-System-Replay

Der bestehende V8-Replay bleibt eine eingefrorene historische Drei-Paare-
Research-Evidenz und wird nicht auf V12.20 umetikettiert.

Er handelt weiterhin nur:

- BTC/USDT
- ETH/USDT
- SOL/USDT

Sein Runtime-Vertrag darf aber erkennen, dass die **heutige** Dry-run-Whitelist
inzwischen zehn Paare besitzt. Dadurch bleibt die alte Baseline reproduzierbar,
ohne den aktuellen Bot künstlich wieder auf sechs oder drei Paare zu begrenzen.

Historische Daten/Replay:

```bat
HISTORISCHE_DATEN_LADEN.bat
HISTORISCHER_LIVE_REPLAY.bat
```

Replay-Ergebnisse liegen unter:

```text
runtime\user_data\replay_results\
```

## Paper-vs-Replay und Deep Research

Der Replay ist kein Ersatz für Freqtrade-Backtests. Er dient der chronologischen
Prüfung von Zustands-, Risk-, Execution- und Reconciliation-Pfaden.

Wenn ein echter überlappender Paper-Zeitraum vorhanden ist:

```bat
PAPER_REPLAY_PARITAET.bat
```

Unerklärte Signal- oder Risk-Allow/Reject-Abweichungen bei identischem kausalem
Input bleiben Release-Blocker für spätere Promotion.

Der verbindliche Research-Plan bleibt:

`RESEARCH_MASTERPLAN_DE.md`

Der Soll/Ist-Abgleich der Deep-Research-Infrastruktur bleibt:

`docs/DEEP_RESEARCH_GAP_AUDIT_DE.md`

## Sicherheitsgrenzen

Aktuell zwingend:

- Dry-run/Paper only;
- Binance Spot;
- USDT;
- long-only;
- kein Hebel;
- kein Futures/Margin;
- pro Entry höchstens 80 USDT;
- global höchstens 240 USDT offen;
- höchstens drei erfolgreiche Entries bei BTC/ETH/LINK/TRX, sonst genau ein
  erster Entry je offenem Trade;
- Zusatz-Entry nur auf einem neuen Signal;
- kein blindes DCA/Martingale;
- Hard-Stop -5,5 %;
- bestehende Pair-Protections;
- lokaler Kill-Switch;
- API nur auf localhost;
- exakter Strategy-Hash;
- gesperrte Strategy-/Config-Inputs;
- keine Exchange-Secrets im Dry-run;
- Live-Overlay nicht automatisch promovieren.

## Nächste Reihenfolge

1. Die aktuell grünen CI-/Runtime-/Safety-Checks bei jeder Änderung grün halten.
2. Den exakten V12.20-Kandidaten im Paperbetrieb mit allen zehn Coins laufen
   lassen; fertig gespeicherte identische Backtests nicht wiederholen.
3. V12.20 für die noch fehlenden 1-/2-/3-Jahres-Fingerprints je Coin messen.
4. Selektives Gewinn-Pyramiding in echter Dry-run-Telemetrie prüfen.
5. SOL, LTC und BCH nacheinander mit jeweils genau einer neuen,
   vorregistrierten Hypothese untersuchen. V12.21 nicht wiederholen.
6. Jede neue Pair-Verbesserung anschließend im gemeinsamen
   250/3×80-Zehn-Paare-Systemtest prüfen.
7. Fee-/Stress-/Walk-Forward-/PBO-/DSR-/Paritäts-Gates schließen.
8. Erst danach über Live-Promotion oder spätere Erhöhung von Stake/Slotzahl
   entscheiden.

`NO_TRADE` bleibt der sichere Standard bei unsicheren Daten, Regimen oder
Signalen. ORB-Retest und Ichimoku bleiben getrennte spätere Research-Challenger
und werden nicht ohne eigenes Experiment in V12.20 eingebaut.

## Wichtig für spätere GPT-/Codex-Runden

Nie wieder diese beiden Aussagen verwenden:

- „Alle 10 Backtests bilden ein gemeinsames 2.500-USDT-Portfolio.“ → falsch.
- „Der Paperbot hat pro Coin 250 USDT.“ → falsch.

Richtig ist:

```text
PAPERBOT:
10 Coins → 1 gemeinsames 250-USDT-Wallet → maximal 3×80 insgesamt.

EINZEL-BACKTEST:
1 Coin → eigenes 250-USDT-Testwallet → 1/2/3 Jahre.

ALLE 10 EINZELN TESTEN:
10 unabhängige Einzeltests → jeweils 250 USDT → gleicher ausgewählter Zeitraum.

INTERNER REPLAY-/AUDIT-SYSTEMTEST (kein UI-Knopf):
10 Coins gemeinsam → 1 Wallet 250 USDT → maximal 3×80 insgesamt.
```

Aktuelle Übergabe:

`research/V12_19_PERSISTENT_PAIR_LEARNING_DE.md`

`research/V12_20_SELECTIVE_PYRAMID_DE.md`
