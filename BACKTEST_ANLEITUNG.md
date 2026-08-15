# Backtest in der Testbot-Oberfläche

Der Menüpunkt **Backtest** wird beim normalen `STARTBOT.bat`-Start automatisch in die installierte FreqUI eingeblendet. Er ist Teil des lokalen Testbots und wird aus dem Git-Repository nachinstalliert; ein frischer Clone benötigt keine manuelle Frontend-Anpassung.

Der Backtest ist **keine zweite Trading-Strategie**. Für jeden Lauf wird die aktuell vom Testbot verwendete Datei `runtime/user_data/strategies/CompressionBreakout250.py` neu gehasht und über den exakten Strategy-Loader `runtime/locked_backtest_freqtrade.py` geladen. Ändert sich der Bot-Code, ändert sich damit automatisch auch die im nächsten Backtest verwendete Strategiequelle.

In der Oberfläche können aktuell ausgewählt werden:

- BTC/USDT, ETH/USDT oder SOL/USDT;
- 1, 2 oder 3 Jahre historische Daten.

## Welche Marktdaten wirklich benötigt werden

Der aktuelle Multi-Timeframe-Pfad benötigt für das ausgewählte Pair:

- **15m**: Signal-/Ausführungs-Timeframe der Strategie;
- **1m**: ausschließlich Freqtrade-Detail-Timeframe für realistischere Intracandle-Fills, Stops und Callbacks;
- **1h**: informatives Trend-/Regime-Timeframe;
- **4h**: informatives Trend-/Regime-Timeframe.

Bei ETH/USDT und SOL/USDT wird zusätzlich **BTC/USDT 4h** als Marktregime geladen. Vor dem sichtbaren Backtestfenster werden derzeit 75 Tage Warmup angefordert, damit insbesondere längere 4h-Indikatoren im sichtbaren Fenster bereits belastbar berechnet werden können.

## Wie ältere und aktuelle Daten vervollständigt werden

Ein Audit am 15.08.2026 zeigte, dass ein vermeintlicher Drei-Jahres-Lauf tatsächlich nur 733 Tage getestet hatte. Ursache war nicht die Strategie, sondern die historische Datenpflege: Freqtrade hatte vorhandene Dateien am aktuellen Ende aktualisiert, die ältere fehlende Historie vor dem lokalen Datenbeginn aber nicht automatisch ergänzt.

Der aktuelle Ablauf ist deshalb zweistufig:

1. vorhandene Binance-Daten werden bis zum aktuellen Ende aktualisiert;
2. die angeforderte ältere Historie wird zusätzlich mit Freqtrades `--prepend`-Pfad ergänzt.

Ein Lauf darf anschließend nur als erfolgreich gelten, wenn **beide** Prüfungen bestehen:

### 1. Kerzendaten-Integrität vor dem Backtest

Die tatsächlich von Freqtrade verwendeten Feather-Dateien werden vor dem Start geprüft. Der Backtest bricht fail-closed ab, wenn im benötigten Fenster mindestens eine der folgenden Bedingungen verletzt ist:

- Datei fehlt oder ist leer;
- Zeitstempel sind nicht streng aufsteigend;
- doppelte Kerzenzeitstempel;
- ein erwartetes 1m-/15m-/1h-/4h-Intervall fehlt;
- der benötigte Warmup-/Startbereich ist nicht abgedeckt;
- das aktuelle Datenende ist zu alt.

Die erfolgreiche Prüfung wird im Ergebnis als `data_integrity_validated=true` gespeichert; zusätzlich werden pro geprüfter Datei Timeframe, Zeilenzahl im benötigten Fenster, erste/letzte Kerze, Duplikate und Lücken dokumentiert.

### 2. Tatsächlich von Freqtrade simulierter Zeitraum nach dem Backtest

Nach dem Lauf werden `backtest_start`, `backtest_end` und `backtest_days` aus dem echten Freqtrade-Ergebnis gegen den angeforderten Zeitraum geprüft. Ein unvollständiger Drei-Jahres-Lauf kann damit nicht mehr lediglich deshalb als „Fertig“ erscheinen, weil die Oberfläche drei Jahre angefordert hatte.

## Referenzprüfung der Dateigröße

Die Größe einer Feather- oder ZIP-Datei ist **kein** Nachweis dafür, ob drei Jahre vollständig vorhanden sind. Im Audit wurde derselbe historische Datensatz unabhängig über Binances öffentlichen Market-Data-Pfad erneut geladen und geprüft. Für BTC, ETH und SOL lagen je Pair alle vier Timeframes ohne Duplikate, unsortierte Zeitstempel oder fehlende Intervalle vor. Die 1m-Dateien enthielten jeweils ungefähr 1,688 Millionen Kerzen vom 01.06.2023 bis 15.08.2026. Dadurch ist belegt, dass relativ kleine Feather-/ZIP-Dateien trotzdem mehrere Millionen vollständige OHLCV-Zeilen enthalten können.

Maßgeblich bleiben daher immer Zeitstempel, Kerzenzahl, Lückenprüfung und der tatsächliche Freqtrade-Testzeitraum — nicht die Dateigröße.

## Backtestparameter

Der normale UI-Backtest verwendet weiterhin:

- 250 USDT Startkapital;
- aktuell konfigurierte Stake-/Positionsgrenzen;
- die aktuellen Freqtrade-Protectons der Strategy;
- `--fee 0.002`, also einen bewusst konservativen Kostenproxy von 0,2 % je Orderseite;
- `--timeframe-detail 1m`;
- `--cache none`, sodass die Simulation selbst bei jedem Lauf neu berechnet wird;
- Export der Resultate getrennt unter `runtime/user_data/backtest_results/ui/<Run-ID>/`.

Angezeigt werden unter anderem Gewinn/Verlust, Rendite, Endkapital, Tradezahl, Profit Factor, Trefferquote, maximaler Drawdown sowie der tatsächliche Freqtrade-Zeitraum und die bestätigte Candle-Integrität.

Nur ein UI-Backtest kann gleichzeitig laufen. Der laufende 24/7-Dry-run bleibt davon getrennt und handelt weiter ausschließlich mit Testgeld. Der Backtest lädt keine Binance-API-Schlüssel und kann keine Echtgeldorder senden.

## Was der Backtest nicht beweist

Auch ein vollständig validierter historischer Backtest ist kein perfektes Live-Replay. OHLCV-Daten enthalten keine historische Orderbuch-Warteschlange, keine echte Netzwerklatenz und keine vollständige Tick-Historie. Das 1m-Detail-Timeframe verbessert die Intracandle-Simulation, ersetzt diese Informationen aber nicht.

Außerdem laufen die datei-/DB-basierten Runtime-Entry-Guards absichtlich nur in `live`/`dry_run`. Der globale Tagesverlust-Guard des laufenden Bots wird daher nicht aus einer historischen Paper-DB nachgebaut. Die normale UI testet zudem jeweils ein ausgewähltes Pair; vor einer Kapitalfreigabe ist zusätzlich ein gemeinsamer BTC+ETH+SOL-Portfolio-Test erforderlich.

Der in `CODEX_NEXT_PHASE_LIVE_REPLAY_DE.md` beschriebene streng chronologische historische Live-Replay/Zeitmaschinen-Modus bleibt deshalb eine zusätzliche Validierungsstufe. Der klassische Backtest ist wichtig und jetzt fail-closed gegen unvollständige Historie gehärtet, aber er ist kein Echtgeld-Freigabeschein.
