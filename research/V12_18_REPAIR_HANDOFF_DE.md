# V12.18 – Reparaturübergabe für Paperbot und Backtests

Stand: 23. August 2026
Branch: `agent/v12-17-ten-pair-research-ui`
Aktive Paper-Strategie: `CompressionBreakout250`, Version `V12.18`
Experiment: `V12.18-TEN-PAIR-PROFIT-PYRAMID-REPAIR`

## Verbindliches Ziel

Der Paperbot beobachtet genau diese zehn Binance-Spot-Paare:

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

Alle zehn Paare teilen sich im Paperbetrieb **eine** virtuelle Wallet mit 250
USDT. Ein Entry-Block beträgt höchstens 80 USDT. Gleichzeitig dürfen höchstens
drei Blöcke beziehungsweise 240 USDT gebunden sein. Spot, Long-only und 1x
bleiben unverändert. Echtes Geld ist nicht freigegeben.

Der Backtest bietet zwei verschiedene, ausdrücklich getrennte Aussagen:

- **Einzeltest:** ein gewähltes Paar, eine eigene virtuelle 250-USDT-Wallet,
  wahlweise ein, zwei oder drei Jahre.
- **Gemeinsamer Systemtest:** alle zehn Paare konkurrieren chronologisch um
  dieselbe 250-USDT-Wallet und dieselben drei 80-USDT-Blöcke, ebenfalls über
  ein, zwei oder drei Jahre.

Die zusätzliche Zehner-Einzelmatrix führt zehn voneinander unabhängige
Einzeltests aus. Sie ist nur eine Paardiagnose und niemals ein Ersatz für den
gemeinsamen Systemtest.

## Fehler im übernommenen V12.17-Stand

### 1. Falsche Bedeutung von „Alle 10“

Der sichtbare Sammelknopf startete zehn unabhängige Wallets mit nominell 2.500
USDT. Der bereits intern vorhandene `PORTFOLIO`-Pfad war für den Benutzer
versteckt. Dadurch spiegelte „Alle 10“ nicht den Paperbot wider.

### 2. Mögliches Nachkaufen eines Verlusttrades

`adjust_trade_position()` löschte `current_profit` ungenutzt. Ein neues
Entry-Signal konnte deshalb einen weiteren 80-USDT-Block hinzufügen, obwohl der
offene Trade im Minus lag. Das widersprach dem Verbot von DCA/Verlust-Nachkauf.

### 3. Kapitalnutzung bei Mehrfacheinstiegen falsch gemessen

Die Auswertung rechnete den endgültigen Gesamtstake eines Trades rückwirkend ab
dem ersten Einstieg. Wurden der zweite und dritte Block erst Tage später
gefüllt, wurde die Kapitalnutzung zu hoch ausgewiesen.

### 4. Lange Läufe sahen eingefroren aus

Während Freqtrade große 1-Minuten-Datensätze lud oder simulierte, blieb der
Prozentwert minutenlang unverändert. Die API lieferte keinen sichtbaren
Aktivitätsnachweis des Unterprozesses.

### 5. Abgebrochene Sitzungen blieben als „running“ markiert

Der Windows-Lebenszeitschutz beendet den Prozessbaum absichtlich, wenn das
überwachte UI-/Startfenster verschwindet. Bei diesem harten Sicherheitsende kann
der normale `finally`-Block kein Abschlussmanifest mehr schreiben. Alte
Sitzungen blieben deshalb irreführend auf `running`.

### 6. V12.17 war nicht regulär im Trial Ledger registriert

Der Backtest-Adapter erfand den Experimentdatensatz zur Laufzeit. Damit fehlte
die dauerhafte, versionierte Forschungsakte. V12.17 und V12.18 stehen nun als
getrennte Einträge in `research/trial_ledger.csv`.

### 7. Veraltete sichtbare Statusangaben

Die Startausgabe zeigte an einer Stelle nur sechs Paare und die Basisschnittstelle
meldete während eines V12.17-Laufs weiterhin V12.15.

## Reparatur in V12.18

### Profit-only Pyramiding

Ein zweiter oder dritter Block im selben Coin ist nur zulässig, wenn alle
folgenden Bedingungen gleichzeitig erfüllt sind:

- das Paar erzeugt auf einer späteren geschlossenen Kerze erneut das normale
  vollständige Entry-Signal;
- der bestehende Trade und der aktuelle Entry-Kurs liegen im Gewinn;
- der neue Entry-Kurs liegt strikt über **jedem** zuvor gefüllten Entry-Kurs;
- es existiert kein offener Auftrag;
- der Trade besitzt weniger als drei erfolgreiche Entries;
- nach weiteren 80 USDT bleiben Gesamteinsatz und Walletgrenzen eingehalten;
- Kill-Switch und Tagesverlustschutz erlauben neue Entries.

Damit ist ein zusätzlicher Block echtes Pyramiding in einen steigenden Gewinner.
Ein Verlust-Nachkauf oder ein tieferer Wiedereinstieg wird fail-closed abgelehnt.

### Echter Zehn-Paare-Systemtest

Der Button `Alle 10 zusammen` sendet das Ziel `PORTFOLIO`. Die Basisschnittstelle
löst dieses Ziel auf exakt alle zehn Whitelist-Paare auf. Freqtrade erhält eine
gemeinsame `--dry-run-wallet 250`, `max_open_trades = 3`, `stake_amount = 80`,
1-Minuten-Detail, 0,2 Prozent Gebühr je Orderseite und aktivierte Protections.

Der Button `10 Einzeltests` bleibt für die separate Paarmatrix erhalten. Seine
Ergebnisse dürfen nicht addiert und als gemeinsames Wallet ausgegeben werden.

### Nachweis der tatsächlich genutzten Blöcke

Neue Ergebnisfelder dokumentieren:

- gesamte Entry-Blöcke;
- zusätzliche Blöcke nach dem Ersteinstieg;
- Trades mit mehreren Entries;
- maximale Entries in einem Trade;
- maximal gleichzeitig aktive Entry-Blöcke;
- maximal gleichzeitig gebundenes Kapital;
- Gewinn, Trades und Entry-Blöcke je Paar.

Die Kapitalzeit wird anhand der tatsächlichen Füllzeit jedes Entry-Orders
berechnet. Entry-Gebühren werden aus dem exportierten Bruttokostenwert entfernt,
damit der gebundene Stake mit Freqtrades Walletrechnung übereinstimmt. Ein
Ergebnis wird abgelehnt, wenn mehr als drei Blöcke oder mehr als 240,05 USDT
gemessen werden.

### Sichtbarer Laufzustand

Die Backtest-API überwacht den gestarteten Download-/Backtest-Unterprozess. Die
UI zeigt Stufenlaufzeit, letzte Logaktivität und ob der Unterprozess lebt. Ein
lange unveränderter Prozentwert ist dadurch nicht mehr mit einem Stillstand zu
verwechseln.

Beim nächsten `STARTBOT.bat`-Start markiert das Cleanup verwaiste Manifeste ohne
lebenden Supervisor als `interrupted`. Es startet dadurch keinen Bot und löscht
keine Handelsdaten.

## Diagnose der Laptop-Sitzung vom 23. August 2026

Die gelesene Sitzung `20260823T160515Z-pid-18600` startete korrekt mit:

- Dry-run und ohne Echtgeldmöglichkeit;
- Strategiehash `772084097ef7...` (V12.17);
- allen zehn Paaren;
- 250 USDT Wallet, 80 USDT je Block, höchstens drei Blöcken;
- einem bereits offenen simulierten BTC-Trade.

Freqtrade schrieb bis 18:55:46 jede Minute einen normalen Heartbeat. Es gab
keinen Beleg für eine festgefahrene Handelsiteration. Danach existierten Prozess
und Port nicht mehr, das Manifest blieb jedoch wegen des harten Endes auf
`running`.

Der BTC-Dreijahrestest rechnete von ungefähr 18:06 bis 18:28. Sein Rohresultat
war 250 → 416,48 USDT, 14 Trades und 24 Entry-Blöcke. Dieses Ergebnis ist **keine
akzeptierte Evidenz**, weil der alte Laptop-Commit den `.venv`-Abhängigkeitsraum
im Dateiaudit falsch behandelte und den Lauf deshalb formal verwarf. Der danach
begonnene ETH-Test wurde vor dem Ergebnis beendet.

Ein unabhängiger GitHub-LINK-Dreijahrestest der V12.17-Quelle ergab 250 → 308,99
USDT, 30 Trades und 26,02 Prozent Drawdown. Auch dieses Einzelresultat beweist
weder die Zehner-Matrix noch die gemeinsame Walletleistung von V12.18.

## Erster formaler V12.18-Nachweis

Nach der Reparatur lief der offizielle gesperrte UI-Backtestpfad einmal für BTC
über ein Jahr:

- Run: `20260823T174151Z-5048432d`
- Fingerprint:
  `ac857d20608e391c35d9aec4e14e94f13e1dca33666a0e7b3414c83b9666f57a`
- Zeitraum: 23.08.2025 bis 23.08.2026, 365 Tage
- 250 → 248,1414 USDT, also −1,8586 USDT beziehungsweise −0,7435 Prozent
- 3 Trades, 0 Gewinner, Profit-Faktor 0, maximaler Drawdown 0,74 Prozent
- 3 Entry-Blöcke insgesamt, keine zusätzliche Pyramiding-Stufe
- maximal 79,7165 USDT gleichzeitig gebunden
- Kapitalzeit 0,09 Prozent, Zeit ohne Position 99,73 Prozent
- exakte V12.18-Quelle, Config-Kette und alle vier erwarteten BTC-Candle-Dateien
  gelesen; keine unerwartete Repo-Datei, kein Kindprozess, Audit bestanden

Damit sind Ablauf, Strategiequelle und Einjahresauswahl technisch bewiesen. Das
finanzielle Ergebnis ist klar schwach und darf weder schöngeredet noch identisch
wiederholt werden. Es zeigt außerdem, dass BTC in diesem jüngsten Jahr kaum
passende Signale lieferte. Der Fingerprint steht deshalb im versionierten
Laufregister.

Die normalen GitHub-CI-Prüfungen führen keine langen finanziellen Backtests mehr
automatisch bei jedem Push aus. Der doppelte LINK-Dreijahresjob wurde aus der
UI-Vertrags-CI entfernt; der verbleibende End-to-End-Lauf ist bewusst nur noch
manuell startbar. Dadurch bleiben schnelle technische Gates automatisch, ohne
identische Finanzsimulationen im Kreis zu wiederholen.

V12.18 bleibt eine technische und sicherheitsbezogene Reparatur. Es existiert
noch kein akzeptierter finanzieller V12.18-Zehn-Paare-Portfoliolauf. Aussagen
wie „V12.18 ist profitabler“ oder „das Ziel ist erreicht“ wären daher falsch.

Insbesondere fehlen weiterhin:

- neue V12.18-Einzeltests für die noch offenen Paar-/Jahreszellen; BTC 1 Jahr
  ist abgeschlossen und gesperrt;
- der echte gemeinsame Zehn-Paare-Test für ein, zwei und drei Jahre;
- vollständige Datei-/Kerzen-Audits dieser Läufe;
- Kostenstress, Walk-Forward/Blind-Evidenz und Paper-/Replay-Parität;
- eine Paar-für-Paar-Entscheidung über LINK, TRX, LTC und BCH.

## Verbindliche Reihenfolge für die Fortsetzung

1. Technische Tests, Syntax, Ruff, Runtime- und Safety-Verträge grün halten.
2. Exakten V12.18-Hash und Git-Commit festhalten.
3. Den abgeschlossenen BTC-1J-Fingerprint niemals erneut ausführen.
4. Die übrigen gewünschten Einzelzellen 1/2/3 Jahre ausführen und vollständig
   archivieren.
5. Danach `PORTFOLIO` mit allen zehn Paaren und einer Wallet für 1/2/3 Jahre.
6. Paarbeitrag, Blocknutzung, Verlustcluster, Drawdown, Kapitalzeit und
   Slot-Verdrängung gemeinsam auswerten.
7. Schlechte neue Paare einzeln ablehnen oder nur mit einem **neuen,
   preregistrierten** Experiment verändern. Nicht mehrere Schwellen gleichzeitig
   nachoptimieren.
8. Erst nach Replay-/Execution-/Robustheitsgates über eine Paper-Promotion
   entscheiden. Echtgeld bleibt gesperrt.

## Unveränderte Forschungsgrenzen

Der eingefrorene V8-Referenzhash bleibt erhalten. `NO_TRADE` bleibt der sichere
Standard bei unklaren Daten oder Signalen. ORB-Retest und Ichimoku bleiben
separate spätere Challenger und werden nicht in diese Reparatur gemischt. DCA,
Martingale, Futures, Margin, Shorts und automatische Kapitalerhöhung bleiben
verboten.

## Sicherheitsnachtrag zum lokalen Start

`STARTBOT.bat` gibt das lokale FreqUI-Passwort nicht mehr im Konsolenfenster
aus und startet die PowerShell-Helfer nicht mehr mit `ExecutionPolicy Bypass`.
Bei einer neuen Installation erzeugt der erste Start weiterhin eine zufällige,
von Git ignorierte lokale Passwortdatei, startet den Bot damit aber noch nicht.
Der Nutzer setzt zuerst über `PASSWORT_AENDERN.bat` ein eigenes Passwort und
startet danach erneut. Diese Änderung betrifft nur den nächsten lokalen Start;
eine bereits laufende Bot-Instanz wurde nicht angefasst.

## Reparatur der leeren FreqUI

Die leere Trade-/Dashboard-/Chart-Ansicht war kein Zehn-Paare- oder
Strategiefehler. Der laufende Bot meldete über seine API zehn Whitelist-Paare,
Dry-run und eine aktive Paper-Position. Die API akzeptierte aber den öffentlich
dokumentierten Platzhalter `LOCAL_ENV_REQUIRED` statt des lokalen Passworts.
Ursache war die Prozess-Umgebungsbereinigung in
`runtime/scripts/start-testbot-24x7.ps1`: Sie entfernte vor dem Freqtrade-Start
auch die vier ausdrücklich erlaubten lokalen `FREQTRADE__API_SERVER__*`-Werte.
Damit konnte die FreqUI-Autoanmeldung keine Markt-, Paar-, Chart- oder
Dashboarddaten laden, während die getrennte Backtest-Seite sichtbar blieb.

Der Startvertrag bewahrt jetzt ausschließlich Benutzername, Passwort,
JWT-Secret und WebSocket-Token der an `127.0.0.1` gebundenen FreqUI. Exchange-
Schlüssel und fremde Cloud-/API-Geheimnisse bleiben aus dem Kindprozess
entfernt. Ein Regressionstest prüft beide Seiten dieses Vertrags. Die
Korrektur wird erst beim nächsten kontrollierten Neustart aktiv; der während
der Diagnose laufende Paper-Bot und seine Position wurden nicht verändert.

## Zweite FreqUI-/Marktdatenreparatur

Der Neustart `20260823T185336Z-pid-17540` bewies, dass die vier lokalen
API-Variablen nun korrekt bis Freqtrade gelangen. FreqUI und API starteten, die
Zehn-Paare-Whitelist sowie der vorhandene BTC-Papertrade wurden geladen. Danach
beendete Binance jedoch alle 30 OHLCV-WebSocket-Abos (zehn Paare mal
15m/1h/4h) mit Close-Code 1008. Der spätere Prozesscode `-1` war die erwartete
Zwangsbeendigung durch den Lebensdauer-Wächter, nachdem das UI-Fenster
geschlossen worden war; er war nicht die ursprüngliche Datenursache.

Das öffentliche Dry-run-Overlay setzt deshalb jetzt ausdrücklich
`exchange.enable_ws` auf `false`. Laut Freqtrade-Vertrag werden OHLCV-Kerzen
dann per REST-Fallback geladen. Strategie, Pairliste, Zeitrahmen, Paper-Wallet,
Positionslimits und Backtestdaten bleiben unverändert. Der STARTBOT-Validator
verlangt diesen Wert, damit ein späterer Config-Umbau die fehlerhafte
WebSocket-Fan-out-Konfiguration nicht unbemerkt zurückbringt.

Der externe FreqUI-Login normalisiert außerdem einen bereits gespeicherten
lokalen Bot-Eintrag auf `Testbot`, wählt ihn aus und lädt die UI genau einmal
neu, wenn Auswahl oder Metadaten veraltet waren. Die Cache-Version des Hooks
wird nun aus seinem vollständigen Inhalt berechnet; damit kann der Browser nach
einem Codeupdate nicht mehr dieselbe alte Hook-URL wiederverwenden.

## Dritte FreqUI-Reparatur: Initialisierungsreihenfolge

Der nächste Paper-Start bewies einen gesunden Backendbetrieb ohne
WebSocketfehler: zehn Paare wurden geladen, die REST-API war online, der
vorhandene BTC-Papertrade wurde fortgesetzt und Heartbeats liefen weiter. Die
vom dauerhaft wiederverwendeten Edge-App-Profil gerenderte Trade-Seite blieb
jedoch leer. Ein unabhängiger Test derselben laufenden URL in einem frischen
Browserprofil zeigte dagegen sofort `Testbot - Online`, alle zehn Paare, den
BTC-Trade, Kurse und Chartdaten. Damit war die verbleibende Ursache auf die
Frontend-Initialisierung des alten Profils eingegrenzt.

Bei einem noch gültigen gespeicherten Token konnte der Login-Hook bisher ohne
Reload enden. Zu diesem Zeitpunkt hatte das vorher geladene FreqUI-Modul seinen
leeren Zustand bereits initialisiert. Der Hook setzt nun pro Browser-Sitzung
eine `sessionStorage`-Marke und erzwingt beim ersten Laden genau einen Reload,
nachdem Bot-Eintrag und Auswahl geschrieben wurden. Beim zweiten Laden ist die
Marke vorhanden; dadurch startet FreqUI mit der fertigen Verbindung, ohne eine
Reload-Schleife zu erzeugen. Der bestehende Inhalts-Hash ändert zugleich die
Hook-URL und verhindert die Wiederverwendung der vorherigen JavaScript-Datei.

## Vierte FreqUI-Reparatur: neues isoliertes Edge-Profil

Auch nach dem Einmal-Reload blieb ausschließlich das automatisch gestartete
Edge-App-Fenster leer, während ein frisches Browserprofil an derselben laufenden
API weiterhin die vollständige Oberfläche zeigte. Der Supervisor verwendet
daher nicht mehr das historisch belastete Verzeichnis `browser-profile`,
sondern dauerhaft `browser-profile-v2` unter den lokalen DaviddTech-Appdaten.
Das erzeugt genau einmal einen sauberen FreqUI-Zustand und behält ihn für
folgende Starts bei. Das alte Profil wird bewusst nicht automatisch gelöscht;
der Patch verändert weder den laufenden Bot noch Browserdaten außerhalb des
eigenen Testbot-Appbereichs. Der Wechsel wird erst beim nächsten kontrollierten
Start über `STARTBOT.bat` aktiv.

## Erfolgreiche UI-Endprüfung mit Profil v2

Am 23.08.2026 wurde das nicht mehr verwendete lokale Testbot-Verzeichnis
`%LOCALAPPDATA%\DaviddTech\AiTradingAgent\browser-profile` nach Prüfung auf
laufende Benutzer vollständig entfernt. Persönliche Edge-Profile, Paper-DB,
Backtests und Auditlogs blieben unangetastet. Anschließend wurde ausschließlich
die normale `STARTBOT.bat` gestartet. Die neue Sitzung
`20260823T193131Z-pid-11492` erreichte `RUNNING`; alle zehn Whitelist-Paare
wurden geladen und der vorhandene BTC-Papertrade wurde fortgesetzt.

Die UI-Endprüfung bestätigte `Testbot - Online`, den korrekten Botnamen, die
vollständige Trade-Seite, den offenen BTC-Trade, Dashboard, Logs und Backtest-
Navigation. Der Chartselektor enthielt alle zehn Paare. BTC, ETH, SOL, XRP, BNB,
DOGE, LINK, TRX, LTC und BCH wurden einzeln ausgewählt und jeweils im Chart
gerendert. Alle laufenden Edge-Prozesse des Testbots verwendeten ausschließlich
`browser-profile-v2`; das alte Profil wurde nicht neu angelegt.

Beim Wechsel zwischen FreqUI-Seiten können Freqtrades interne API-WebSockets
mit `WebSocketDisconnect` 1006 schließen und upstream einen Stacktrace loggen.
Das ist vom zuvor behobenen Binance-OHLCV-WebSocketfehler 1008 zu unterscheiden:
Marktdaten, REST-API, UI und Botbetrieb liefen während der Endprüfung weiter.

## Fünfte FreqUI-Reparatur: erwartete Seitenwechsel ohne Fehler-Stacktrace

Die abschließende Prüfung aller UI-Bereiche bestätigte weiterhin einen
laufenden Bot, korrekte Dashboarddaten, alle zehn Whitelist-Paare und zehn
einzeln gerenderte Charts. Trade, Dashboard, Logs und Chart öffnen jeweils eine
eigene interne API-WebSocket-Verbindung. Beim Seitenwechsel schließt der Browser
diese Verbindung planmäßig. Die gepinnten Starlette-/Uvicorn-Versionen melden
diesen normalen Client-Abbruch dennoch als `ERROR` mit
`WebSocketDisconnect(code=1006)`.

Der gesperrte Dry-run-Start installiert nun einen eng begrenzten Logging-Filter.
Er blendet ausschließlich Uvicorns Meldung `Exception in ASGI application` aus,
wenn die Exception-Kette den erwarteten `ClientDisconnected` oder exakt den
WebSocket-Code 1006 enthält. Andere Uvicorn-, Freqtrade-, Exchange- und
WebSocketfehler bleiben unverändert sichtbar. Die Änderung beeinflusst weder
Orders noch Marktdaten, Strategieentscheidungen oder Backtests und wird erst
beim nächsten normalen `STARTBOT.bat`-Start aktiv.
