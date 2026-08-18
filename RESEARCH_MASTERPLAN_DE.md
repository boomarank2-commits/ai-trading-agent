# Verbindlicher Research-Masterplan

Stand: 18.08.2026

## 1. Ein aktueller Weg

Der aktive Entwicklungszweig ist `agent/v12-adaptive-league`.

V12 ist die **Research-Schicht** für robuste Pair-/Strategy-Auswahl. Die tatsächlich vom Testbot geladene Strategy-Datei ist aktuell weiterhin `CompressionBreakout250.py` mit `STRATEGY_VERSION = "V11"`.

V11 ist kein bestätigter Gewinner. Es ist der aktuelle ausführbare Research-/Paper-Kandidat, bis eine neue Version ausdrücklich promoviert und anschließend lokal verifiziert wurde.

Historische Versionen V8, V9, V10 und frühere V11-Zustände bleiben als Baseline/Trial-Evidenz erhalten. Sie sind keine parallelen aktiven Roadmaps.

## 2. Zielarchitektur

Der Bot soll keine ständig handelnde Universalstrategie sein, sondern ein deterministisches System:

```text
Market Data
→ Data Quality
→ pair-lokale Features
→ pair-lokales Regime
   ├─ TREND/BREAKOUT
   ├─ RANGE/MEAN_REVERSION
   └─ NO_TRADE
→ geeignete validierte Strategy-Familie
→ Signal-/Cost-Gate
→ Portfolio & Risk
→ Execution / OMS
→ Reconciliation
→ Telemetrie
```

BTC, ETH und SOL entscheiden unabhängig. BTC-Regime darf ETH/SOL nicht steuern.

`NO_TRADE` ist ein gewünschter Zustand, wenn keine robuste Netto-Edge vorliegt.

## 3. Hot Path / Cold Path

### Hot Path

Der Tradingpfad bleibt deterministisch. Kein LLM darf spontan Orders, Risk, Stopps, Positionsgröße oder aktive Parameter verändern.

### Cold Path

```text
Historische Daten + Trades + Telemetrie
→ Hypothese
→ Candidate/Family
→ Development
→ Validation
→ Blind/Holdout
→ rolling Walk-Forward
→ Kosten-/Lag-/Robustheitsstress
→ Trial Ledger
→ explizite Promotion
→ exakter lokaler Freqtrade-Gegentest
```

AI dient der Hypothesenerzeugung und Analyse, nicht der ungeprüften Live-Selbstmodifikation.

## 4. Sicherheitsvertrag

- Binance Spot / USDT
- long-only, 1x
- kein Futures, Margin oder Short
- kein DCA / Martingale
- 250 virtuelle USDT
- maximal 80 USDT je Position
- maximal drei offene Positionen / 240 USDT Exposition
- kein automatisches Kapital-Skalieren
- keine automatische Echtgeldfreigabe
- Hard-Stop und Risk-Grenzen dürfen nicht nur deshalb gelockert werden, damit ein Backtest besser aussieht

## 5. Research-Zielgröße

Primäres wirtschaftliches Ziel ist **robuster Netto-USDT-Gewinn nach Kosten**.

Eine hohe In-Sample-Zahl allein reicht nicht. Ein Kandidat muss möglichst viele der folgenden Prüfungen bestehen:

- Profit Factor > 1 und positive Expectancy nach Baseline-Kosten
- zusätzliche Kostenbelastung
- Development/Validation/Blind-Trennung
- mehrere Walk-Forward-Folds
- Pair- und Jahresslices
- Max Drawdown und Time-under-Water
- Family-/Trade-/PnL-Konzentration
- 1-Bar-Lag bzw. Execution-Delay
- Parameter-Nachbarschaft/Plateau
- keine Future-Leakage / kein Repainting
- 1m-Detail im finalen lokalen Freqtrade-Test
- PBO/Deflated Sharpe, wenn das Trial-Universum ausreichend vollständig ist

Je höher der robuste Netto-USDT-Gewinn, desto besser. Eine Variante mit höherem Trainingsgewinn, aber negativem Blindtest ist schlechter als eine niedrigere, robuste Variante.

## 6. Pair-spezifische Optimierung

BTC, ETH und SOL dürfen unterschiedliche Gewinnerfamilien und Parameter haben.

Beispiel:

```text
BTC → langsamer Trend → Donchian/Breakout
ETH → Trend → Ichimoku
SOL → Range → Bollinger MR
```

Das ist erlaubt, wenn jede Zuordnung unabhängig aus den Pair-Daten hervorgeht und OOS/Walk-Forward trägt.

## 7. Strategy-Familien

Die Deep-Research-Grundlage liefert mehrere Hypothesen. Sie werden als getrennte Familien behandelt:

- langsamer Donchian-/Breakout-Trend
- Ichimoku Trend
- Bollinger Mean Reversion
- weitere vorregistrierte Challenger nur mit klarer Hypothese

ORB/FVG/BOS/Panic/Pullback sind keine Pflichtbestandteile. Eine Familie, die wiederholt Kosten oder Blindtests nicht überlebt, wird quarantänisiert/rejected statt immer weiter nachgetunt.

## 8. V12 Research League

V12 darf viele Kandidaten schnell untersuchen, aber nicht den aktiven Bot während der Suche verändern.

Mindestens:

```text
Development
→ Validation
→ Candidate Freeze
→ Blind
```

und zusätzlich rolling Walk-Forward über verschiedene Marktphasen.

Ein Blind-/Holdout-Fenster gilt als verbraucht, sobald sein Ergebnis eine weitere Parameteränderung beeinflusst hat. Danach darf es für diese Experimentlinie nicht mehr als unangetasteter Blindtest bezeichnet werden.

## 9. Historische Baselines

Die eingefrorene V8-Baseline bleibt unter `research/baselines/V8/` erhalten und darf nicht überschrieben werden. Ihr Nutzen ist Vergleich, Reproduzierbarkeit und Trial-Historie – nicht die Behauptung, sie sei weiterhin die aktive Strategy.

V9/V10/V11-Ergebnisse und weitere Fehlschläge bleiben im `research/trial_ledger.csv` dokumentiert.

Negative Versuche werden nicht gelöscht.

## 10. Replay / Execution / Parität

Der Full-System-Replay bleibt wichtig für Zustands-, Risk-, Restart- und Execution-Fragen. Er ersetzt den normalen Freqtrade-Backtest nicht.

Wichtige Anforderungen:

- monotone Simulationszeit
- nur geschlossene Candles
- deterministischer Restart/Checkpoint
- Data-Manifest/Hashes
- Fee-/Spread-/Delay-Stress
- Partial-Fill-/Cancel-/Reconciliation-Tests
- Paper-/Replay-Parität, wenn überlappende Daten vorhanden sind

Ein historisches OHLCV-Replay ist keine perfekte Tick-/Orderbuch-Rekonstruktion. Diese Grenze muss sichtbar bleiben.

## 11. Promotion

Ein Research-Kandidat wird erst aktive Strategy, wenn:

1. seine Hypothese und Parameter feststehen;
2. Development/Validation/Blind/Walk-Forward ausreichend robust sind;
3. Kosten- und Execution-Stress nicht die Edge zerstören;
4. Trial-/Robustheitsdiagnostik keine klare Overfit-Warnung liefert;
5. der Kandidat als neue Strategy-Version/Hash festgeschrieben ist;
6. der exakte Kandidat lokal mit Freqtrade und 1m-Detaildaten erneut getestet wurde;
7. eine manuelle Entscheidung zur Promotion erfolgt.

Kein automatischer Echtgeldschritt.

## 12. Maßgebliche Projektdateien

- `START_HERE_DE.md`
- `RESEARCH_MASTERPLAN_DE.md`
- `docs/DEEP_RESEARCH_GAP_AUDIT_DE.md`
- `research/trial_ledger.csv`
- `runtime/user_data/strategies/CompressionBreakout250.py`
- `runtime/adaptive_pair_optimizer.py`
- `runtime/adaptive_family_league.py`

Die große zusammengeführte Deep-Research-Datei aus den vier Trading-Videos soll als feste Referenz unter `docs/DEEP_RESEARCH_MASTER_DE.md` versioniert werden, sobald sie in den Branch übernommen ist.

## 13. Repository-Hygiene

- eine aktuelle Startanleitung
- ein aktueller Masterplan
- historische Evidenz in `research/` bzw. klar benannten Docs
- keine parallelen offenen PRs für bereits verworfene Versionen
- keine generierten Marktdaten, Logs, Datenbanken oder Backtest-Artefakte in Git
- keine alte Statusdatei im Root, wenn sie nur einen überholten Zwischenstand wiederholt

Der aktuelle Weg ist: **V12 Research → robuste Pair-Kandidaten → exakter lokaler Freqtrade-Test → manuelle Promotion.**
