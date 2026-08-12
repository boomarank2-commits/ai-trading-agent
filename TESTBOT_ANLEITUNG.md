# Testbot per Doppelklick starten

## Was `STARTBOT.bat` startet

Ein Doppelklick auf [`STARTBOT.bat`](STARTBOT.bat) startet ausschließlich
Freqtrade im **Dry-run**. Der Bot liest öffentliche Binance-Marktdaten, gibt
aber keine echten Orders auf und benötigt keine Binance-API-Schlüssel.

Zusätzlich bleibt das Konsolenfenster mit den laufenden Freqtrade-Meldungen
offen und die lokale FreqUI-Weboberfläche wird automatisch im Standardbrowser
geöffnet. Die Oberfläche läuft ausschließlich auf diesem Rechner unter
`http://127.0.0.1:8080`.

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

Nach dem Start wartet `STARTBOT.bat`, bis die lokale Freqtrade-API wirklich
bereit ist, und öffnet dann automatisch `http://127.0.0.1:8080` im Browser.
Das Konsolenfenster bleibt gleichzeitig geöffnet und zeigt weiterhin die
laufenden Meldungen und Heartbeats.

Für die ausschließlich lokale Paper-Test-Oberfläche gelten:

- Benutzer: `testbot`
- Passwort: `PaperOnly-250-USDT!`
- Adresse: `http://127.0.0.1:8080`

Die API bindet ausdrücklich nur an `127.0.0.1` und wird nicht im Netzwerk oder
Internet veröffentlicht. Falls der Browser ausnahmsweise nicht automatisch
aufgeht, kann die Adresse manuell im Browser geöffnet werden, sobald im
Konsolenfenster `state='RUNNING'` bzw. ein Bot-Heartbeat erscheint.

FreqUI kann nicht nur Werte anzeigen, sondern besitzt auch Bedienfunktionen.
Für einen unveränderten Beobachtungstest sollten keine manuellen Start-, Stop-,
Force-Entry- oder Force-Exit-Aktionen in der Oberfläche ausgelöst werden.
`force_entry_enable` bleibt im Testbot technisch deaktiviert.

## Erster Start auf einem neuen Rechner

Voraussetzungen sind eine Internetverbindung und Windows WinGet. `STARTBOT.bat`
prüft beim Doppelklick automatisch, ob [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
bereits vorhanden ist. Fehlt `uv`, versucht der Starter es selbst über WinGet
mit `winget install --id=astral-sh.uv -e` zu installieren. Der Benutzer muss
also normalerweise keine Eingabeaufforderung öffnen und keinen Installationsbefehl
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

Der Testbot läuft im geöffneten Konsolenfenster dauerhaft im Vordergrund. Das
Fenster muss geöffnet bleiben. Die Browseroberfläche ist nur eine zusätzliche
Ansicht; das Schließen des Browserfensters beendet den Bot nicht. Solange der
Bot läuft, blockiert der Starter den normalen Windows-Energiesparmodus.
Zuklappen des Laptops, Ruhezustand, Herunterfahren, ein Windows-Neustart oder ein
Stromausfall können den Prozess trotzdem beenden.

Mit **Strg+C im Konsolenfenster** wird der Testbot sauber beendet. Dabei werden
Sitzungsdaten abgeschlossen und ein Bericht erzeugt. Das bloße Schließen des
Konsolenfensters kann den Abschlussbericht überspringen; er lässt sich danach
mit `TESTBOT_AUSWERTUNG.bat` nachholen.

Es gibt keinen automatischen Start nach einem Windows-Neustart. Danach einfach
erneut auf `STARTBOT.bat` doppelklicken. Die persistente Dry-run-Datenbank wird
weiterverwendet; bereits gespeicherte simulierte Trades werden fortgesetzt.
Auch nach einem seltenen fatalen Programmfehler startet der Supervisor nicht
ungefragt neu; das Fenster bleibt mit dem Fehler offen. Nach der Prüfung kann
derselbe Doppelklick die persistente Datenbank wieder aufnehmen.

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

- `tradesv3.dryrun.sqlite`: persistente Freqtrade-Datenbank aller simulierten
  Trades;
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

Die vorhandene Strategie war in den bisherigen historischen Prüfungen negativ.
Dieser Dry-run dient dazu, Funktion, Stabilität und Verhalten zu beobachten.
Weder ein mehrtägiger Lauf noch ein zwischenzeitliches Plus beweist eine
profitable Strategie oder rechtfertigt Echtgeldbetrieb. Der Bot ist damit
weder als identische Kopie des Videos noch als produktionsreifer Handelsbot
ausgewiesen.
