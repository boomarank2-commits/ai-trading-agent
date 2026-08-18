# Start hier: aktueller V12-Research-Zweig

## Ein klarer Arbeitsweg

Der aktuelle Entwicklungszweig ist `agent/v12-adaptive-league`.

Wichtig: V12 ist derzeit **Research-Infrastruktur**, noch keine promovierte neue Trading-Strategie. Die aktuell von `STARTBOT.bat` geladene Strategy-Datei ist weiterhin `CompressionBreakout250.py` mit `STRATEGY_VERSION = "V11"`.

V11 ist ein pair-lokaler, deterministischer Router:

- BTC/USDT, ETH/USDT und SOL/USDT entscheiden unabhängig voneinander.
- Jedes Pair nutzt nur seine eigenen 15m/1h/4h-Daten.
- Regime: `TREND/BREAKOUT`, `RANGE/MEAN_REVERSION`, `NO_TRADE`.
- Familien: `ORB_RETEST`, `ICHIMOKU_TREND`, `BOLLINGER_MR`.
- Spot, long-only, kein Hebel, kein DCA/Martingale.
- 250 virtuelle USDT, maximal 80 USDT je Position, maximal drei Positionen.

V11 ist **kein bestätigter Gewinner**. Die V12-Forschung dient dazu, bessere und robustere Pair-spezifische Kandidaten mit Development/Validation/Blind- und Walk-Forward-Logik zu finden.

## Maßgebliche Dateien

1. `RESEARCH_MASTERPLAN_DE.md` – verbindlicher Entwicklungs-/Research-Rahmen.
2. `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md` – Soll/Ist und offene technische Lücken.
3. `research/trial_ledger.csv` – Historie der getesteten, verworfenen und offenen Kandidaten.
4. `runtime/user_data/strategies/CompressionBreakout250.py` – tatsächlich vom Bot geladene Strategy-Quelle.
5. `runtime/adaptive_pair_optimizer.py` und `runtime/adaptive_family_league.py` – V12-Research-Suche, nicht Live-Hotpath.

Historische Versionen V8/V9/V10/V11 bleiben nur als Evidenz/Trial-Historie relevant. Sie sind keine vier parallelen aktiven Entwicklungswege.

## Bot starten

```bat
STARTBOT.bat
```

Der normale UI-Backtest verwendet die tatsächlich aktive Strategy-Quelle und keine separate Schönwetter-Strategie.

## Research / Replay

Die vorhandenen Replay-, Daten-, Auswertungs- und Statistik-Helfer bleiben Werkzeuge für reproduzierbare Forschung:

```bat
HISTORISCHE_DATEN_LADEN.bat
HISTORISCHER_LIVE_REPLAY.bat
HISTORISCHE_AUSWERTUNG.bat
STATISTIK_AUDIT.bat
```

Sie sind keine alternativen Trading-Bots.

## Sicherheitsvertrag

- Binance Spot / long-only / 1x.
- Kein Futures, Margin, Short, Hebel, DCA oder Martingale.
- Kein automatischer Echtgeld-Release.
- Kein LLM im synchronen Orderpfad.
- Neue Kandidaten werden erst nach reproduzierbaren Backtests, Kostenstress, Walk-Forward/Blind-Evidenz und manueller Freigabe promoviert.
- `NO_TRADE` bleibt eine gültige und gewünschte Entscheidung.

## Aktuelle Reihenfolge

1. V12-Research-Ergebnisse sauber auswerten.
2. Nur robuste Pair-/Family-Kandidaten weiterführen.
3. Verlierer im Trial Ledger dokumentieren und nicht erneut als aktiven Weg behandeln.
4. Gewinner anschließend mit dem exakten lokalen Freqtrade-Backtest inklusive 1m-Detaildaten gegenprüfen.
5. Erst danach über eine Änderung der aktiven Strategy entscheiden.

Marktdaten, Datenbanken, Logs, Secrets und generierte Backtest-Artefakte bleiben lokal und gehören nicht in Git.
