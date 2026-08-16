# Testbot per Doppelklick starten

## Was `STARTBOT.bat` startet

Ein Doppelklick auf [`STARTBOT.bat`](STARTBOT.bat) startet ausschließlich
Freqtrade im **Dry-run**. Der Bot liest öffentliche Binance-Marktdaten, gibt
aber keine echten Orders auf und benötigt keine Binance-API-Schlüssel.

Zusätzlich bleibt das Konsolenfenster mit den laufenden Freqtrade-Meldungen
offen und die lokale FreqUI-Weboberfläche wird automatisch als eigene
Edge-/Chrome-App geöffnet. Die Oberfläche läuft ausschließlich auf diesem
Rechner unter `http://127.0.0.1:8080`.

Die festen Testeinstellungen sind:

- 250 virtuelle USDT Startkapital;
- höchstens drei gleichzeitig offene Positionen;
- höchstens 80 virtuelle USDT je Position und 240 USDT Gesamtexposition;
- neue Entries werden nach 10 virtuellen USDT realisiertem Tagesverlust gesperrt;
- Stop-Loss bei 5,5 Prozent unter dem Einstieg;
- ausschließlich `BTC/USDT`, `ETH/USDT` und `SOL/USDT` auf Binance Spot.

Das ist ein simulierter Forward-Test mit echten öffentlichen Marktdaten, kein
Echtgeldbetrieb. Der Starter lädt keine Schlüssel und kann mit diesen
Einstellungen kein Echtgeld handeln.

## FreqUI im Browser

Nach dem Start wartet der lokale Supervisor, bis die Freqtrade-API wirklich
bereit ist, und öffnet dann automatisch `http://127.0.0.1:8080` als eigene
Browser-App. Dafür wird Microsoft Edge oder Google Chrome benötigt. Der
Supervisor verwendet ein separates lokales Browserprofil nur für den Testbot.
Das Konsolenfenster bleibt gleichzeitig geöffnet und zeigt weiterhin die
laufenden Meldungen und Heartbeats.

Für die ausschließlich lokale Paper-Test-Oberfläche gelten:

- Benutzer: `testbot`
- Passwort: `PaperOnly-250-USDT!`
- Adresse: `http://127.0.0.1:8080`

Die API bindet ausdrücklich nur an `127.0.0.1` und wird nicht im Netzwerk oder
Internet veröffentlicht. Die Browser-App ist gleichzeitig Teil des
Lebenszeitschutzes: Wird dieses überwachte Testbot-UI geschlossen, beendet der
Supervisor auch den Bot. Ein manuell zusätzlich geöffnetes normales Browser-Tab
unter derselben Adresse ersetzt diese überwachte App nicht.

FreqUI kann nicht nur Werte anzeigen, sondern besitzt auch Bedienfunktionen.
Für einen unveränderten Beobachtungstest sollten keine manuellen Start-, Stop-,
Force-Entry- oder Force-Exit-Aktionen in der Oberfläche ausgelöst werden.
`force_entry_enable` bleibt im Testbot technisch deaktiviert.

## Erster Start auf einem neuen Rechner

Voraussetzungen sind eine Internetverbindung, Windows WinGet und Microsoft Edge
oder Google Chrome. `STARTBOT.bat` prüft beim Doppelklick automatisch, ob
[`uv`](https://docs.astral.sh/uv/getting-started/installation/) bereits vorhanden
ist. Fehlt `uv`, versucht der Starter es selbst über WinGet mit
`winget install --id=astral-sh.uv -e` zu installieren. Der Benutzer muss also
normalerweise keine Eingabeaufforderung öffnen und keinen Installationsbefehl
von Hand eingeben.

Falls WinGet selbst auf dem Rechner fehlt oder die automatische Installation
nicht erfolgreich abgeschlossen werden kann, stoppt der Starter mit einer klaren
Fehlermeldung und startet keinen Bot.

Nach erfolgreicher `uv`-Prüfung gleicht der Starter die lokale Umgebung bei jedem
Start mit `uv.lock` ab. Fehlt die lokale `.venv`, führt er automatisch

```powershell
uv sync --frozen --all-extras --python 3.12
```

aus. Dadurch wird die in `uv.lock` festgelegte Python-3.12-Umgebung angelegt.
Abhängig von Internetverbindung und Rechner kann der erste Start einige Minuten
dauern; spätere unveränderte Prüfungen sind deutlich kürzer.

Fehlt die FreqUI-Weboberfläche in der lokalen Freqtrade-Installation, führt der
Setup-Pfad zusätzlich einmalig den offiziellen Befehl `freqtrade install-ui`
aus. Danach startet Freqtrade automatisch. Spätere Starts installieren die UI
nicht erneut, solange sie vorhanden ist.

## Betrieb und Beenden

Der Testbot läuft nur, solange seine sichtbaren Lebensanker vorhanden sind. Vor
dem eigentlichen Botstart setzt der Supervisor ein Windows Job Object mit
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Dadurch dürfen Freqtrade, Python und die
zugehörigen lokalen Hilfsprozesse den Supervisor nicht überleben.

Folgende Regeln gelten:

- **Strg+C im Konsolenfenster**: kontrollierter Shutdown; Sitzungsdaten werden
  abgeschlossen und der Abschlussbericht wird erzeugt.
- **Konsolenfenster über X schließen**: Fail-closed; Windows beendet den gesamten
  Bot-Prozessbaum. Der Bot darf danach nicht unsichtbar im Hintergrund laufen.
- **Testbot-UI schließen**: Der UI-Wächter beendet den Supervisor; dadurch wird
  ebenfalls der gesamte Bot-Prozessbaum beendet.
- **Supervisor abstürzen oder per Taskkill beendet werden**: Das Windows Job
  Object beendet verbleibende Bot-Child-Prozesse automatisch.
- **Bot endet kontrolliert**: Die überwachte Testbot-Browser-App wird zusammen
  mit dem Supervisor ebenfalls geschlossen.

Bei einem abrupten Fenster-/Prozessabbruch hat die sofortige Beendigung des Bots
Vorrang vor einem Abschlussbericht. Die persistente Dry-run-Datenbank bleibt
erhalten und `TESTBOT_AUSWERTUNG.bat` kann die vorhandenen Daten danach separat
auswerten. Ein kontrolliertes Beenden mit Strg+C bleibt der bevorzugte Weg,
wenn das Fenster noch verfügbar ist.

Solange der Bot läuft, blockiert der Starter den normalen Windows-Energiesparmodus.
Zuklappen des Laptops, Ruhezustand, Herunterfahren, ein Windows-Neustart oder ein
Stromausfall können den Prozess trotzdem beenden.

Es gibt keinen automatischen Start nach einem Windows-Neustart. Danach einfach
erneut auf `STARTBOT.bat` doppelklicken. Die persistente Dry-run-Datenbank wird
weiterverwendet; bereits gespeicherte simulierte Trades werden fortgesetzt.
Auch nach einem seltenen fatalen Programmfehler startet der Supervisor nicht
ungefragt neu. Nach der Prüfung kann derselbe Doppelklick die persistente
Datenbank wieder aufnehmen.

## Weitere Doppelklick-Dateien

- [`STOP_NEUE_TESTTRADES.bat`](STOP_NEUE_TESTTRADES.bat) sperrt neue
  simulierte Entries. Bereits offene Testpositionen werden weiter verwaltet.
  Der getrennte Echtgeld-Kill-Switch wird dabei nicht verändert.
- [`TESTTRADES_FREIGEBEN.bat`](TESTTRADES_FREIGEBEN.bat) entfernt nur diese
  Test-Entry-Sperre und erlaubt dem laufenden oder nächsten Dry-run wieder neue
  simulierte Entries.
- [`TESTBOT_AUSWERTUNG.bat`](TESTBOT_AUSWERTUNG.bat) erstellt jederzeit eine
  neue Gesamtauswertung der persistenten Testdatenbank. Das funktioniert auch,
  wenn der Bot gerade nicht läuft.

## Gespeicherte Daten und Berichte

Die Ergebnisse bleiben lokal unter `runtime/user_data/` erhalten:

- `tradesv8.dryrun.sqlite`: eigene persistente Freqtrade-Datenbank des V8-Paper-Forward-Tests. Alte V2/V3-Datenbanken bleiben getrennt erhalten und werden nicht in die V8-Auswertung gemischt;
- `logs/sessions/<Sitzungs-ID>/freqtrade.log`: Freqtrade-Protokoll der Sitzung;
- `logs/sessions/<Sitzungs-ID>/supervisor.log`: Start-, Laufzeit- und
  Abschlussmeldungen;
- `logs/sessions/<Sitzungs-ID>/session-manifest.json`: Zeiten, Einstellungen,
  Pfade und Hashes der verwendeten Strategie, Konfiguration und Abhängigkeiten;
- `logs/sessions/<Sitzungs-ID>/dryrun-report-<Sitzungs-ID>.json`: strukturierter
  Bericht für eine spätere maschinelle Analyse;
- `logs/sessions/<Sitzungs-ID>/dryrun-report-<Sitzungs-ID>.md`: lesbare
  Auswertung derselben Sitzung;
- `logs/reports/`: manuell mit `TESTBOT_AUSWERTUNG.bat` erzeugte JSON- und
  Markdown-Gesamtberichte.

Die Berichte berechnen Gewinn und Verlust nur aus geschlossenen simulierten
Trades sowie bereits realisierten Teilverkäufen offener Trades. Teilverkäufe
offener Trades erscheinen im Gesamtwert, können ohne Order-Zeitstempel aber
nicht sicher einer einzelnen Sitzung zugeordnet werden. Unrealisiertes P/L
(Gewinn oder Verlust) noch offener Positionen ist ausdrücklich ausgeschlossen.
Der Bericht bezeichnet `250 USDT + realisiertes Ergebnis` deshalb als
Kapitalwert, nicht als aktuellen Wallet- oder Marktwert.

## Ergebnisse richtig einordnen

Die Strategie handelt selten. Auch nach 24 Stunden können **null Trades** ein
technisch normales Ergebnis sein; für eine aussagekräftigere Beobachtung kann
der Test mehrere Tage laufen.

Der aktuelle V8-Kandidat ist eine langsame 4h-Donchian-Trendstrategie und wurde
vor dem Paper-Start deutlich breiter geprüft als die verworfenen V1–V7-Varianten.
Unter dem konservativen historischen Kostenproxy blieb das gemeinsame
BTC/ETH/SOL-Portfolio unter anderem im Drei-Jahres-, älteren Holdout- und
Fünf-Jahres-Test positiv. Die Detailzahlen und Gegenbeispiele stehen in
`docs/V8_PAPER_CANDIDATE_REPORT_DE.md`.

Das ist trotzdem **kein Profitversprechen**. Die Strategie besitzt eine niedrige
Trefferquote, kann lange Verlustserien haben und war in einzelnen historischen
Jahresslices negativ. Wenige große Trends tragen einen wesentlichen Teil des
Ertrags. Genau deshalb startet V8 in einer frischen `tradesv8.dryrun.sqlite` und
muss zuerst unverändert im Paper-Forward-Test bestehen. Ein mehrtägiges Plus,
ein einzelner großer Gewinner oder ein guter Backtest rechtfertigt weiterhin
keinen Echtgeldbetrieb.
