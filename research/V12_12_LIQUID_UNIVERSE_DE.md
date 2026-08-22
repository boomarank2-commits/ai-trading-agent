# V12.12 – kontrollierte Erweiterung des liquiden Spot-Universums

## Vorregistrierte Frage

Kann dieselbe V12.9-Logik die 250 USDT sinnvoll häufiger einsetzen, wenn drei
weitere liquide und historisch ausreichend lange Binance-Spot-Märkte zugelassen
werden, ohne Ertrag und Drawdown des bisherigen Drei-Pair-Portfolios zu
verschlechtern?

## Einzige Strategieänderung

- unverändert: BTC/ETH/SOL-Logik, sämtliche Schwellen, Reclaim-Regeln, Exits,
  −5,5-%-Hard-Stop, 80 USDT je Position und maximal drei Positionen;
- neu: XRP/USDT, BNB/USDT und DOGE/USDT;
- die drei neuen Pairs nutzen ausschließlich den schon vorhandenen breiten,
  langsamen Donchian-Kern von SOL;
- kein neuer Indikator, kein neues Exit-Modell und kein nachträgliches Tuning.

Die Auswahl erfolgte vor dem Backtest anhand öffentlichen Binance-Spot-
Volumens über 24 Stunden, 90 und 365 Tage sowie mindestens drei Jahren
Historie. Das ist nur eine Zulassungsvoraussetzung und kein Profitbeweis.

| Pair | 24h Quote-Volumen | Median 90 Tage | Median 365 Tage |
|---|---:|---:|---:|
| XRP/USDT | 990,9 Mio. USDT | 78,1 Mio. USDT | 160,0 Mio. USDT |
| BNB/USDT | 351,8 Mio. USDT | 62,6 Mio. USDT | 98,1 Mio. USDT |
| DOGE/USDT | 262,4 Mio. USDT | 34,3 Mio. USDT | 88,6 Mio. USDT |

Zeitpunkt der öffentlichen Binance-Abfrage: 22.08.2026 vor dem Lauf. Alle drei
Pairs deckten das benötigte Drei-Jahres-Fenster vollständig ab.

## Erfolgskriterien vor dem Lauf

Der exakt einmal ausgeführte Drei-Jahres-Gesamtportfolio-Test muss:

1. Kapitalzeit über 17,42 % erhöhen und Zeit ganz ohne Position unter 66,96 %
   senken;
2. mindestens 158,154 USDT Nettogewinn erreichen;
3. maximalen geschlossenen Drawdown unter 15 % halten;
4. mit XRP, BNB und DOGE zusammen positive Attribution und bei mindestens zwei
   der drei neuen Pairs positive Attribution liefern;
5. den neuen Dateizugriffsaudit vollständig bestehen.

## Laufkontrolle

Der gesperrte Runner bindet den Strategy-Hash
`e56c2b87cd76b5e33a481957d288236afdc9421e669dcd4b536d4ccb6cb93524`.
Er protokolliert die tatsächlich geöffneten Strategy- und Config-Dateien. Die
nativen Candle-Ladevorgänge werden an Freqtrades eigener Dateinamen-Grenze mit
Hash vor und nach dem Ladevorgang gebunden. Ein anderes Pair, eine unerwartete Repo-Datei oder ein Kindprozess
macht den Lauf ungültig. Während des Laufs wird zusätzlich der sichtbare
Prozessbaum kontrolliert. Ergebnis und Entscheidung werden nach dem ersten Lauf
hier ergänzt; ein Fehlschlag wird nicht durch spontane Schwellenänderungen
repariert.

## Ergebnis des einzigen Laufs

Run `20260822T072248Z-df00496d` simulierte exakt den vorregistrierten
V12.12-Hash über 1.095 Tage. Der Prozessbaum bestätigte den isolierten Runner,
die zwei vorgesehenen Configs, alle sechs Pairs, 1m-Detail, 0,002 Kosten je
Orderseite, 250 USDT und den eigenen Ergebnisordner.

| Kennzahl | V12.9 Referenz | V12.12 Diagnose | Veränderung |
|---|---:|---:|---:|
| Nettogewinn | 158,154 USDT | 288,646 USDT | +130,492 USDT |
| Trades | 87 | 122 | +35 |
| Profit Factor | 2,32 | 2,48 | +0,16 |
| Kapitalzeit | 17,42 % | 23,61 % | +6,19 Punkte |
| Zeit ohne Position | 66,96 % | 61,25 % | −5,71 Punkte |
| geschlossener Drawdown | 7,98 % | 9,62 % | +1,64 Punkte |
| Wallet-Drawdown | 15,44 % | 14,42 % | −1,02 Punkte |

Attribution der neuen Pairs: XRP +106,760 USDT bei 12 Trades, DOGE +30,335
USDT bei 18 Trades und BNB +14,148 USDT bei 16 Trades. Damit waren alle drei
neu zugelassenen Märkte positiv und lieferten zusammen +151,243 USDT.

Die Qualitätswarnung ist deutlich: Insgesamt gab es 22 Gewinner und 100
Verlierer sowie maximal 34 Verluste in Folge. Besonders der bereits zuvor
problematische ETH-Reclaim verlor erneut 22,210 USDT bei 28 Verlusten aus 29
Trades. Die höhere Kapitalnutzung löst somit noch nicht das Ziel „weniger
schlechte Trades“.

## Auditentscheidung

Der neue Python-Datei-Hook bestätigte exakte Strategy, Hash, Configs,
Ausgabedateien, keine fremden Repo-Dateien und keine durch den gesperrten Runner
gestarteten Kindprozesse. Er sah jedoch keine Feather-Dateien, weil Arrow diese
unterhalb von Pythons `open`-Hook nativ lädt. Der Laufvertrag markierte das
Ergebnis deshalb korrekt als fehlgeschlagen. Die positive Simulation bleibt
diagnostische Evidenz, ist aber kein formal vollständig bestandener Backtest.

Die Infrastruktur wurde anschließend ohne neuen Strategielauf repariert:
Künftige Läufe protokollieren den Dateinamen direkt an Freqtrades
`_load_ohlcv_dataframe`-Grenze, speichern SHA-256, Größe, Änderungszeit und
Ladezahl und prüfen den Hash nach dem Lauf erneut. Zusätzlich wird Freqtrades
`.last_result.json` nicht mehr fälschlich als eigentliche Ergebnisdatei gewählt.
Der identische V12.12-Lauf wird nicht wiederholt und bleibt durch seinen
Fingerabdruck blockiert.

Die veröffentlichte Strategy-Datei wurde danach ausschließlich mechanisch auf
LF-Zeilenenden normalisiert, damit ihr Hash nach Git-Pull auf jedem Rechner
stabil bleibt. Ihr veröffentlichter SHA-256 ist
`9978cbcc00af80bb77933f8246cd9e78c73ef1d54b0a60e0b8f24e85e8f39993`;
Logik und materieller Test-Fingerabdruck sind gegenüber dem diagnostischen
Lauf unverändert. Dessen tatsächlich ausgeführter Rohdatei-Hash `e56c2b87…`
bleibt im Laufregister erhalten.
