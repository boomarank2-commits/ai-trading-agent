# V12.17 – aktuelle GPT-/Codex-Übergabe

Stand: 23.08.2026

Dieses Dokument beschreibt ausschließlich den **aktuellen Soll- und Istzustand**
der V12.17-Arbeit. Die lange historische Entwicklung V12.12–V12.16 bleibt in
`research/CONTINUATION_HANDOFF_DE.md`, dem Trial Ledger und den einzelnen
Research-Dokumenten erhalten.

## Aktueller Branch

Arbeitsbranch:

`agent/v12-17-ten-pair-research-ui`

Basis:

`agent/v12-adaptive-league` bei
`c5f7f890cc08233be0a7fecf5b86f9902ef0fd72`

Draft-PR: `#24`

Nicht mergen, solange die vollständigen Runtime-/Backtest-/Replay-Verträge nicht
grün sind.

## Nicht mehr verhandelbare Begriffs-Trennung

### A. Laufender Paper-/Dry-run-Bot

Ein einziges gemeinsames virtuelles Wallet:

- 250 USDT insgesamt;
- 80 USDT je Entry-Block;
- höchstens 240 USDT gleichzeitig gebunden;
- höchstens drei 80-USDT-Blöcke über alle zehn Coins;
- ein Coin darf einen zweiten oder dritten 80er erhalten, wenn später erneut ein
  vollständiges normales Entry-Signal entsteht;
- kein Zusatzkauf nur wegen eines Verlustes;
- Spot, long-only, 1x;
- Echtgeld bleibt nicht promoviert.

### B. Normaler Backtest

Jeder Coin wird **für sich** getestet:

- eigenes virtuelles Startwallet 250 USDT;
- 1, 2 oder 3 Jahre auswählbar;
- exakt aktuelle V12.17-Strategy;
- Sammelknopf `Alle 10 nacheinander` startet zehn unabhängige Tests mit dem
  aktuell gewählten Zeitraum;
- jeder Lauf startet erneut mit 250 USDT;
- die nominellen 2.500 USDT über zehn Simulationen bilden **kein gemeinsames
  Portfolio**.

### C. Späterer Gesamt-Systembacktest

Separater Test, nicht Teil des normalen Sammelknopfs:

- alle zehn Paare chronologisch;
- ein gemeinsames 250-USDT-Wallet;
- maximal 3×80 insgesamt;
- dieselbe Zusatz-Entry-Logik im selben Coin;
- misst Slot-/Kapital-Konkurrenz des Paperbots.

Diese drei Ebenen nie wieder miteinander vermischen.

## Aktive zehn Paare

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

ADA ist wegen des abgelehnten V12.16-Portfolioversuchs nicht erneut in das
aktuelle Universum aufgenommen.

## Aktive Dateien

Strategy:

`runtime/user_data/strategies/CompressionBreakout250.py`

Config:

`runtime/user_data/config.json`

Dry-run-Validator:

`runtime/validate_dryrun_config.py`

Backtest-API-Unterbau:

`runtime/testbot_backtest_api.py`

V12.17-Zehn-Paare-Adapter:

`runtime/ten_pair_backtest_api.py`

Backtest-UI:

`runtime/ui/testbot-backtest.js`

Locked Paper-Loader:

`runtime/locked_freqtrade.py`

## Strategy V12.17

Die aktive Klasse heißt weiterhin `CompressionBreakout250`, damit STARTBOT und
die gesperrte Loader-Kette nicht auf einen parallelen Strategy-Pfad wechseln.

Wesentliche Änderungen gegenüber V12.15:

- `STRATEGY_VERSION = "V12.17"`;
- ALLOWED_PAIRS auf zehn erweitert;
- LINK/TRX/LTC/BCH zunächst in `BROAD_CORE_PAIRS`;
- BTC/ETH Spezialpfade und Reclaims bleiben erhalten;
- bekannte abgelehnte Familien werden nicht reaktiviert;
- `position_adjustment_enable = True`;
- `max_entry_position_adjustment = 2`;
- maximal drei erfolgreiche Entries je offenem Pair;
- Zusatz-Entry nur bei einer späteren neuen `enter_long`-Signalcandle;
- `Trade.total_open_trades_stakes()` begrenzt globale Exposure weiterhin auf
  240 USDT.

## Wichtige Freqtrade-Eigenschaft

Zusätzliche Position-Adjustments innerhalb eines bereits offenen Freqtrade-
Trades verbrauchen keinen weiteren `max_open_trades`-Slot. Deshalb darf sich die
Sicherheitslogik nicht allein auf `max_open_trades = 3` verlassen. V12.17 prüft
zusätzlich die gesamte aktuell gebundene Stake-Summe gegen 240 USDT.

Dadurch ist z. B. erlaubt:

- LINK 160 + XRP 80;
- BTC 240;
- BTC 80 + ETH 80 + SOL 80.

Nicht erlaubt ist jede Kombination über 240 USDT.

## Backtest-UI

Das Dropdown enthält alle zehn Coins. Das Periodendropdown enthält 1/2/3 Jahre.

`Backtest starten`:

- genau ein ausgewähltes Pair;
- eigenes 250-USDT-Wallet.

`Alle 10 nacheinander`:

- liest einmal die aktuell gewählte Jahreszahl;
- erzeugt zehn Fälle `(pair, years)`;
- führt sie sequenziell aus;
- keine PORTFOLIO-Zelle in der normalen UI.

Der interne `PORTFOLIO`-Target im API-Unterbau bleibt absichtlich erhalten, um
später den gemeinsamen 250/3×80-Systemtest durchführen zu können.

## Paper-/Live-Sicherheit

V12.17 ist Paper-/Dry-run only.

`runtime/user_data/config-live.example.json` wird **nicht** automatisch auf
Position Adjustment umgestellt. Der alte Live-Overlay ist deshalb mit der
V12.17-Paper-Strategy absichtlich nicht startfähig. Das ist ein Safety Gate und
kein Fehler.

Der exakte Locked Loader, Strategy-Hash, Config-Prüfung, localhost-FreqUI,
Kill-Switch, Spot/long-only-Vertrag und fehlende Exchange-Secrets bleiben
bestehen.

## Historische Evidenz nicht überschreiben

- V8 bleibt eingefrorene historische Drei-Paare-Baseline.
- Der V8-Replay bleibt auf BTC/ETH/SOL; er erkennt lediglich, dass die heutige
  Dry-run-Whitelist inzwischen zehn Paare enthält.
- V12.15 bleibt historische akzeptierte Sechs-Paare-Referenz.
- V12.16 ADA bleibt REJECT.
- Alte Fingerprints und Audit-Artefakte nicht löschen oder umetikettieren.

## Aktueller Prüfstatus während dieser Umsetzung

Bereits während des Umbaus bestätigt:

- Backtest-/UI-Verträge liefen nach der Trennung erfolgreich durch;
- der neue Strategy-Guard testet explizit zweiten 80er bei frischem LINK-Signal,
  Ablehnung auf derselben Signalcandle, Ablehnung ohne Signal, Ablehnung ab drei
  Entries und Ablehnung oberhalb 240 USDT;
- der frühere Live-Loader-Test wurde korrigiert: Dry-run muss V12.17 akzeptieren,
  der noch nicht promovierte Live-Overlay muss V12.17 ablehnen;
- Replay-Altverträge werden nur an den neuen aktiven Whitelist-/Versionsstand
  angepasst, nicht in ihrer historischen Strategie umgebaut.

Vor einer Merge-/Promotion-Entscheidung immer die GitHub-Checks des aktuellen
Head-Commits prüfen. Keine Aussage „alles grün“ aus einem älteren Head übernehmen.

## Nächste zulässige Schritte

1. Alle CI-Checks des aktuellen V12.17-Heads grün bekommen.
2. STARTBOT sichtbare Statusausgabe auf V12.17/zehn Paare aktualisieren, ohne den
   Startpfad zu verändern.
3. Paperbot mit den zehn Paaren im Dry-run starten.
4. Neue simulierte Entries und insbesondere Mehrfach-Entries desselben Coins
   beobachten und protokollieren.
5. Independent Backtests für LINK/TRX/LTC/BCH über 1/2/3 Jahre durchführen.
6. Pair-spezifische Anpassungen einzeln, vorregistriert und nachvollziehbar
   testen.
7. Danach separaten finalen gemeinsamen 250/3×80-Systemtest durchführen.
8. Erst danach über Live-Promotion oder spätere Stake-/Slot-Skalierung sprechen.

## Unzulässige Abkürzungen

- keinen separaten 250-USDT-Topf je Coin im Paperbot erzeugen;
- keinen normalen „Alle 10“-Backtest als gemeinsames Wallet ausgeben;
- keine Backtest-Ergebnisse zehnfach addieren und Portfolio nennen;
- keine Zusatz-Entries allein wegen Verlusten;
- keine Live-Promotion durch bloße Config-Kopie;
- keine ADA-Wiederholung auf identischem Fingerprint;
- keine Schwellen nach Sicht auf dasselbe historische Ergebnis so lange drehen,
  bis der Coin profitabel aussieht.

Weitere aktuelle Details:

- `docs/ZEHN_PAARE_ROADMAP_DE.md`
- historischer Langverlauf: `research/CONTINUATION_HANDOFF_DE.md`
- Experimente: `research/trial_ledger.csv`
- ausgeführte Fingerprints: `research/executed_test_fingerprints.csv`
