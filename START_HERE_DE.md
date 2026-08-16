# Start hier: V8-Paperbot und Research-System

## Aktueller Stand

Der aktuelle Champion ist `CompressionBreakout250` / V8.

V8 bleibt eingefroren und läuft ausschließlich im simulierten Paper-/Dry-run-Betrieb mit:

- Binance Spot / USDT
- BTC/USDT, ETH/USDT, SOL/USDT
- long-only, 1x
- 250 virtuelle USDT
- maximal 80 USDT je Position
- maximal drei Positionen / 240 USDT Gesamtengagement

Status: **READY FOR EXTENDED PAPER TEST – NOT READY FOR REAL MONEY.**

Der verbindliche Weiterentwicklungsplan steht in [`RESEARCH_MASTERPLAN_DE.md`](RESEARCH_MASTERPLAN_DE.md). Ältere Codex-Phasen sind keine aktive Sollvorgabe mehr.

## Testbot starten

Für den 24/7-Paper-Test:

```bat
STARTBOT.bat
```

Der sichtbare STARTBOT-Prozess bleibt Teil des Sicherheitsvertrags: Wird die überwachte Konsole geschlossen, muss der zugehörige Bot-Prozessbaum beendet werden.

Die Bedienung des Paperbots steht in [`TESTBOT_ANLEITUNG.md`](TESTBOT_ANLEITUNG.md).

## Normaler Backtest

Der integrierte Backtest simuliert die aktuell geladene Strategie; es gibt keine separate zweite Backtest-Strategie.

Für lokale historische Backtests kann außerdem verwendet werden:

```bat
HISTORISCHER_BACKTEST.bat
```

## Historischer Full-System-Replay

Der Replay ist kein Ersatz für den klassischen Backtest. Er spielt historische Daten chronologisch ab und führt zustandsabhängige Portfolio-/Risk-/Orderpfade mit.

Zuerst historische Daten laden und prüfen:

```bat
HISTORISCHE_DATEN_LADEN.bat
```

Danach:

```bat
HISTORISCHER_LIVE_REPLAY.bat
```

Der Replay nutzt ein gemeinsames 250-USDT-Wallet für BTC, ETH und SOL und erzeugt seine Ergebnisse unter:

```text
runtime\user_data\replay_results\
```

Für den aktuellen Research-Gate sollen Baseline-Kosten von 0,002 je Orderseite und zusätzlich ein Stresslauf mit 0,004 je Seite bewertet werden.

## Paper-vs-Replay-Parität

Wenn ein tatsächlich überlappender Paper-Zeitraum vorhanden ist:

```bat
PAPER_REPLAY_PARITAET.bat
```

Unerklärte Signal- oder Risk-Allow/Reject-Abweichungen bei identischem kausalem Input sind ein Release-Blocker für spätere Strategie-Promotion.

## Replay-/Research-Auswertung

```bat
HISTORISCHE_AUSWERTUNG.bat
```

Die Auswertung dient insbesondere dazu, die `failed_4h_breakout`-Trades, Volume-Ratio, Breakout-Distanz und kausale Regime zu untersuchen, **ohne V8 dadurch automatisch zu verändern**.

## Trial Ledger und Multiple Testing

Alle Kandidaten – auch abgelehnte – bleiben in:

```text
research\trial_ledger.csv
```

PBO/Deflated-Sharpe-Diagnostik kann über:

```bat
STATISTIK_AUDIT.bat
```

laufen, sobald vergleichbare Return-Serien für mehrere Trials vorliegen. Diese Kennzahlen sind Research-Gates und keine Gewinn- oder Echtgeldfreigabe.

## Was aktuell ausdrücklich nicht gemacht wird

- kein Futures/Perpetuals
- kein Margin
- kein Short
- kein Hebel
- kein Martingale/DCA
- keine automatische Kapitalerhöhung
- kein LLM mit direkter Exchange-Orderfunktion
- kein Mischen von Bollinger/Ichimoku/ORB in den eingefrorenen V8
- kein neues Volume-Tuning nach Sicht auf B1/B2

Bollinger Mean Reversion ist ein späterer **separater Challenger**, nicht Teil des aktuellen V8.

## Tests

Vor relevanten Research-Änderungen:

```bat
uv sync --frozen --all-extras --python 3.12
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
```

Marktdaten, Replay-Ergebnisse, Paper-Datenbanken, Logs und Secrets bleiben lokal und dürfen nicht in Git committed werden.
