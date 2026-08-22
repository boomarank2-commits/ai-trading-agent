# Übergabe- und Entscheidungsprotokoll für die fortlaufende Bot-Verbesserung

Stand: 22.08.2026

## Zweck

Dieses Dokument ist die verbindliche Übergabe für ein späteres GPT/Codex-System.
Es erklärt nicht nur **was** geändert wurde, sondern **warum**, welche Evidenz
bereits vorliegt, welche Tests schon ausgeführt wurden und welcher nächste
Versuch zulässig ist. Zusammen mit `research/trial_ledger.csv` und
`research/executed_test_fingerprints.csv` verhindert es, dass dieselbe Idee
oder derselbe materielle Backtest versehentlich erneut ausgeführt wird.

Ein schöner Gesamtgewinn allein genügt nicht. Jede Version soll gegenüber ihrem
direkten Vorgänger nachvollziehbar mehr Nettogewinn und/oder bessere
Trade-Qualität liefern, ohne Risiko, Kostenannahmen oder Sicherheitsgrenzen
abzuschwächen.

## Unveränderlicher Bot-/Backtest-Paritätsvertrag

Jeder maßgebliche Portfolio-Backtest muss genau den anschließend nutzbaren
Dry-Run-Bot spiegeln:

- aktive Quelle:
  `runtime/user_data/strategies/CompressionBreakout250.py`;
- Binance Spot/USDT, long-only, 1x;
- `dry_run: true`;
- gemeinsames Startguthaben: 250 USDT;
- fester Einsatz: 80 USDT je geöffneter Position;
- maximal drei gleichzeitige Positionen und damit höchstens 240 USDT Exposure;
- BTC, ETH und SOL erhalten bei einem Entry ebenfalls jeweils genau 80 USDT;
- XRP, BNB und DOGE konkurrieren im selben Konto um dieselben drei Slots;
- keine getrennten oder nachträglich addierten 250-USDT-Unterkonten;
- kein Futures, Margin, Short, DCA, Martingale oder automatische
  Kapitalerhöhung;
- Hard-Stop −5,5 %, aktuelle Protections und Exit-Logik;
- 0,002 Gebühr je Orderseite, 15m Strategie, 1m Detail sowie 1h/4h
  Informative-Daten;
- `--cache none` und ein gemeinsamer Portfolio-Lauf;
- exakter Strategy-/Config-/Candle-Dateiaudit muss bestanden sein.

Ein Einzelpair-Test dient nur der Attribution. Die Entscheidung über den
250-USDT-Bot fällt anhand des gemeinsamen Portfolio-Laufs.

## Aktiver Ausgangspunkt: V12.12

Veröffentlichter GitHub-/Desktop-Commit:

`96883ba89c308638a40277609072abd377e55434`

Veröffentlichter Strategy-SHA256:

`9978cbcc00af80bb77933f8246cd9e78c73ef1d54b0a60e0b8f24e85e8f39993`

V12.12 ließ BTC, ETH, SOL, XRP, BNB und DOGE zu. XRP, BNB und DOGE verwenden
ausschließlich den schon vorhandenen langsamen Donchian-Kern. Die Simulation
über 1.095 Tage ergab diagnostisch:

| Kennzahl | V12.12 |
|---|---:|
| Start-/Endkapital | 250 / 538,646 USDT |
| Nettogewinn | +288,646 USDT |
| Trades | 122 |
| Gewinner / Verlierer | 22 / 100 |
| Profit Factor | 2,483 |
| Kapitalzeit | 23,61 % |
| Zeit ohne Position | 61,25 % |
| geschlossener Drawdown | 9,62 % |
| Wallet-Drawdown | 14,42 % |

XRP, BNB und DOGE waren einzeln positiv und lieferten zusammen +151,243 USDT.
Der Lauf blieb trotzdem nur diagnostisch, weil die erste Audit-Version native
Arrow-Dateizugriffe nicht sehen konnte. Diese Audit-Lücke wurde danach im Code
geschlossen. Der materielle V12.12-Fingerabdruck ist gespeichert und darf nicht
erneut ausgeführt werden.

## Vorregistrierter nächster Versuch: V12.13

### Beobachtung

Der zusätzliche ETH-Trend-Reclaim war wiederholt negativ:

- in der früheren V12.9-Auswertung ungefähr −28,93 USDT;
- in V12.12 −22,210 USDT bei 29 Trades, davon 28 Verluste.

Der BTC-Reclaim war in V12.12 dagegen mit +23,598 USDT positiv. Eine globale
Entfernung beider Reclaim-Pfade wäre deshalb keine isolierte, evidenzgestützte
Änderung.

### Falsifizierbare Hypothese

Wenn ausschließlich der ETH-Reclaim deaktiviert wird, während BTC-Reclaim,
alle langsamen Kerne, sechs Pairs, Positionsgrößen, Exits, Stopps und
Protections unverändert bleiben, dann verschwinden viele kleine schlechte
ETH-Trades. Frei bleibende Slots können weiterhin von BTC, SOL, XRP, BNB oder
DOGE genutzt werden. Erwartet werden höherer Nettogewinn, höherer Profit Factor
und weniger Verlusttrades ohne wesentliche Verschlechterung der Kapitalnutzung.

### Einzige zulässige Strategieänderung

- ETH: `reclaim_long` nicht mehr als Entry zulassen;
- BTC: Reclaim unverändert;
- BTC/ETH/SOL/XRP/BNB/DOGE: langsamer Kern unverändert;
- sämtliche Zahlenwerte, Exits, Stopps, Protections und Risikogrenzen
  unverändert.

Keine zweite Signal-, Stoploss-, Take-Profit-, Pair- oder Parameteränderung
darf in V12.13 ergänzt werden.

### Vorab festgelegte Annahmekriterien

Der neue dreijährige Gesamtportfolio-Lauf wird nur als Verbesserung angenommen,
wenn:

1. Datei-/Prozess-/Candle-Audit vollständig besteht;
2. Nettogewinn über +288,646 USDT und Endkapital über 538,646 USDT liegt;
3. Profit Factor mindestens 2,483 erreicht;
4. weniger als 100 Verlusttrades entstehen;
5. Wallet-Drawdown unter 15 % bleibt;
6. Kapitalzeit mindestens 22 % und Zeit ohne Position höchstens 63 % beträgt;
7. kein neues Pair negative Gesamtattribution nur wegen Slot-Verdrängung
   verursacht;
8. Sicherheits- und Paritätsprüfungen vollständig bestehen.

Die Schwellen werden nach Sicht auf das Ergebnis nicht verändert.

### Annahme- und Ablehnungsregel

- **PASS:** Ergebnis und Jahresslices dokumentieren, V12.13 im Trial Ledger
  abschließen, exakt getesteten Strategy-/Config-Stand als neuen aktiven
  Dry-Run-Kandidaten committen und veröffentlichen.
- **FAIL:** Ergebnis und Ursache dauerhaft dokumentieren, Fingerabdruck
  erhalten, ETH-Reclaim-Entfernung nicht in den aktiven Desktop-Bot übernehmen
  und V12.12 als aktiven Stand behalten.
- Ein technischer Auditfehler macht den Lauf formal ungültig. Die gleiche
  materielle Simulation wird trotzdem nicht blind wiederholt; zuerst muss eine
  neue, dokumentierte Entscheidung getroffen werden.

## V12.13-Preflight-Protokoll

Der erste Startversuch wurde am 22.08.2026 **vor Datenabruf, Ergebnisordner
und Simulation** blockiert. Ursache: Das erhaltene V12.12-ZIP enthält den
damals tatsächlich gelaufenen CRLF-Rohstand, während der anschließend nur auf
LF normalisierte und veröffentlichte V12.12-Vorgänger den Rohdatei-SHA
`9978cbcc…` besitzt. Der Logik-Hash blieb gleich, der fail-closed
Quellvergleich verlangt jedoch bewusst den exakten Rohdatei-Hash.

Zulässige Infrastrukturkorrektur vor dem ersten echten V12.13-Lauf:

- zuerst weiterhin im erhaltenen Ergebnis-ZIP nach der exakten Vorgängerquelle
  suchen;
- nur wenn sie dort fehlt, die versionierte Git-Historie des aktuellen
  Repositories durchsuchen;
- ausschließlich einen Git-Blob akzeptieren, dessen SHA-256 exakt dem im Trial
  Ledger registrierten Vorgängerhash entspricht;
- keine Working-Tree-Datei, keine ähnlich aussehende Quelle und keinen
  abweichenden Logik-Hash akzeptieren;
- diesen Fallback automatisiert testen.

Diese Korrektur ändert weder Strategy, Testfingerabdruck, Konfiguration noch
Backtestprotokoll. Der blockierte Preflight war kein Backtest und wird nicht als
ausgeführter materieller Versuch registriert.

## Reihenfolge für V12.13

1. Dieses Dokument und den geplanten Trial-Ledger-Eintrag anlegen.
2. Nur den ETH-Reclaim aus dem Entry-Pfad entfernen.
3. Strategy-/Config-/Runtime-Parität und neue Hashes prüfen.
4. Gesamte Testsuite und Governance ausführen.
5. Genau einen neuen dreijährigen 250-USDT-Portfolio-Backtest starten.
6. Prozessbaum, Strategy, Configs, sechs Pairs und Candle-Dateien während des
   Laufs auditieren.
7. Gesamt-, Pair-, Entry-Tag-, Exit-, Jahres- und Drawdown-Auswertung erstellen.
8. Gegen die oben festgelegten Kriterien entscheiden.
9. Nur bei PASS den getesteten Stand auf
   `agent/v12-adaptive-league` veröffentlichen und den Desktop-Ordner
   fast-forward aktualisieren.

## Bereits sichtbare spätere Hypothesen – noch nicht freigegeben

Diese Ideen dürfen nicht gleichzeitig mit V12.13 umgesetzt werden:

- pair-lokale Verlustcluster anhand der vollständigen V12.13-Attribution neu
  prüfen;
- getrennten flexiblen Stop-/Take-Profit-Challenger auf Basis von MAE/MFE
  vorregistrieren, nicht nach Bauchgefühl;
- Kapitalnutzung durch einen später getrennt validierten Range-Challenger
  erhöhen;
- PnL-Konzentration und Jahresstabilität prüfen, bevor weitere Pairs
  hinzukommen.

Der unmittelbar nächste Versuch nach V12.13 wird erst aus dessen dokumentierter
Attribution abgeleitet. Keine Schwelle und kein Exit wird nachträglich so
gedreht, dass derselbe historische Zeitraum schöner aussieht.

## Abgeschlossenes Ergebnis V12.13

Der einzige materielle Lauf `20260822T121118Z-8c9385d9` verwendete exakt den
vorregistrierten Strategy-Hash
`043916a93ef9aafac3622425496ca2cd75f01c639bb3dc345a79887e882813d9`
und den Testfingerabdruck
`15d9cb240a80169b05020cf115317df54fa4ce66f425223d71bce646dc52c111`.
Der Datei-, Prozess- und Candle-Audit bestand: alle 24 erwarteten Candle-Sätze
für sechs Pairs und vier Timeframes wurden geladen, keine ungeplante Candle-
Datei wurde verwendet, keine Eingabedatei änderte sich während des Laufs und
kein fremder Kindprozess entstand.

| Kennzahl | V12.12 Maßstab | V12.13 | Gate |
|---|---:|---:|---|
| Endkapital | 538,646 USDT | 502,772 USDT | FAIL |
| Nettogewinn | 288,646 USDT | 252,772 USDT | FAIL |
| Profit Factor | 2,4833 | 2,3636 | FAIL |
| Trades | 122 | 103 | Diagnose |
| Verlusttrades | 100 | 82 | PASS |
| geschlossener Max-Drawdown | 9,62 % | 9,24 % | PASS |
| Kapitalzeit | 23,61 % | 23,42 % | PASS |
| Zeit ohne Position | 61,25 % | 61,06 % | PASS |

Entscheidung: **REJECT – nicht in den aktiven Bot übernehmen.** Weniger
Verlusttrades allein reichen nicht, wenn 35,875 USDT Nettogewinn verloren gehen
und der Profit Factor fällt.

### Warum die scheinbar gute Entfernung schlechter wurde

V12.12 und V12.13 hatten 92 identische Trades. V12.13 entfernte wie geplant 29
ETH-Reclaims mit zusammen −22,210 USDT, erzeugte durch die geänderte Reihenfolge
von Slots und Protections aber elf andere Trades. Besonders wichtig:

- Die ETH-Reclaim-Verluste in V12.12 lösten eine pair-lokale
  `LowProfitPairs`-Sperre bis 29.11.2024 aus.
- Diese Sperre verhinderte dort einen ETH-Champion-Trade, der in V12.13 vom
  27.11. bis 19.12.2024 einen der drei Slots belegte und −2,865 USDT verlor.
- Mit dem freien Slot nahm V12.12 stattdessen einen XRP-Trade vom 29.11. bis
  02.12.2024 mit ungefähr +39,998 USDT mit.

Lehre: Entry-Tags dürfen in einem gemeinsamen 250-USDT-Portfolio mit maximal
drei Positionen nicht einfach anhand ihrer isolierten Summe entfernt werden.
Signal, Pair-Sperre und Slotbelegung bilden zusammen die Strategie.

### Ebenfalls diagnostiziert und nicht weiterzuverfolgen

- Ein allgemeiner Verlust-Zeitstopp nach 36 Stunden für ETH beziehungsweise 48
  Stunden für andere Pairs hätte rückgerechnet ungefähr 76,260 USDT gekostet.
  Er hätte unter anderem einen BTC-Gewinner von rund +39,946 USDT und einen
  ETH-Gewinner von rund +40,006 USDT beendet, weil beide am frühen Stichtag
  noch leicht negativ waren.
- ETH-Reclaim-Volumenfilter von 0,70 bis 1,25 hätten den einzigen positiven
  ETH-Reclaim entfernt und nur Verlierer behalten. Auch diese Richtung ist für
  die vorhandene Stichprobe verworfen.

## Vorregistrierter nächster Versuch: V12.14

### Ausgangspunkt und einzige Änderung

V12.14 startet wieder von der besseren, vollständigen V12.12-Logik. ETH- und
BTC-Reclaim, alle sechs Donchian-Kerne, Entry-/Exit-Schwellen, Stoploss,
Positionsgrößen, drei Slots und die komplette Pairliste bleiben wie V12.12.

Die einzige materielle Änderung ist die pair-lokale `LowProfitPairs`-Schwelle:

- bisher: Sperre nach zwei unprofitablen Trades innerhalb von 14 Tagen;
- V12.14: Sperre bereits nach dem ersten unprofitablen Trade innerhalb von 14
  Tagen;
- Sperrdauer bleibt exakt 72 Stunden, `required_profit` bleibt 0,0.

### Falsifizierbare Hypothese

Die V12.13-Chronologie zeigte direkt, dass eine aktive Pair-Sperre einen
schlechteren Slotverbrauch verhindern und einen großen Gewinner eines anderen
Pairs ermöglichen kann. Eine frühere, weiterhin nur pair-lokale Pause soll
Verlustcluster verkürzen, ohne offene Trends durch einen engeren Stop oder ein
Take-Profit abzuschneiden. Sie ist kein nachträglich auf einzelne Kursmarken
angepasster Exit.

### Vorab festgelegte Annahmekriterien

V12.14 wird nur übernommen, wenn der einzige exakte Drei-Jahres-Lauf:

1. den vollständigen Datei-/Prozess-/Candle-Audit besteht;
2. mehr als +288,646 USDT Gewinn beziehungsweise 538,646 USDT Endkapital
   erreicht;
3. mindestens Profit Factor 2,4833 erreicht;
4. weniger als 100 Verlusttrades erzeugt;
5. geschlossenen Drawdown höchstens 10 % und Wallet-Drawdown unter 15 % hält;
6. mindestens 22 % Kapitalzeit und höchstens 63 % Zeit ohne Position erreicht;
7. alle sechs Pairs positiv hält;
8. sämtliche Paritäts-, Sicherheits-, Unit- und Governance-Tests besteht.

Kein Kriterium wird nach Sicht auf das Ergebnis gelockert. Bei FAIL wird V12.14
dokumentiert und der aktive Stand auf V12.12 zurückgesetzt. Der exakte Lauf darf
nicht wiederholt werden.

## Abgeschlossenes Ergebnis V12.14

Run `20260822T123801Z-715d5a9e` bestand den vollständigen Audit. Exakt 24
erwartete Candle-Dateien wurden gelesen, keine unerwartete Datei, kein
veränderter Input und kein Kindprozess wurden beobachtet. Strategy-Hash und
Fingerabdruck entsprachen der Vorregistrierung.

| Kennzahl | V12.12 Maßstab | V12.14 | Gate |
|---|---:|---:|---|
| Endkapital | 538,646 USDT | 491,401 USDT | FAIL |
| Nettogewinn | 288,646 USDT | 241,401 USDT | FAIL |
| Profit Factor | 2,4833 | 2,2603 | FAIL |
| Trades | 122 | 113 | Diagnose |
| Verlusttrades | 100 | 95 | PASS |
| geschlossener Max-Drawdown | 9,62 % | 11,96 % | FAIL |
| Kapitalzeit | 23,61 % | 20,70 % | FAIL |
| Zeit ohne Position | 61,25 % | 65,87 % | FAIL |

Pair-Ergebnisse: BTC +82,642, ETH +53,254, XRP +46,307, DOGE +45,499, BNB
+19,159 und SOL −5,460 USDT. Damit scheiterte zusätzlich das vorab gesetzte
Alle-Pairs-positiv-Kriterium.

Entscheidung: **REJECT – nicht übernehmen.** Die Sperre nach jedem ersten
Verlust beseitigte fünf Verluste, blockierte aber zu viele valide Folgetrends.
Sie reduzierte die Kapitalzeit um 2,91 Prozentpunkte, erhöhte den Drawdown und
machte SOL negativ. Eine globale Verschärfung dieser Pair-Sperre darf nicht
erneut getestet werden.

## Vorregistrierter nächster Versuch: V12.15

### Ausgangspunkt und einzige Änderung

V12.15 startet erneut direkt von der besseren V12.12-Logik. Insbesondere wird
`LowProfitPairs.trade_limit` wieder auf 2 gesetzt. Alle Signale, sechs Pairs,
80-USDT-Positionen, drei Slots, Hard-Stop, ROI, normale Exits und Reclaim-Exits
bleiben unverändert.

Die einzige materielle Änderung ist eine späte Gewinnsicherung ausschließlich
für `champion_donchian`-Trades:

- erst ab mindestens +30 % laufendem Gewinn wird sie aktiviert;
- danach darf der Stop nicht mehr unter +5 % bezogen auf den Einstieg fallen;
- Reclaim-Trades verwenden den Ratchet nicht;
- vor +30 % bleibt der bisherige −5,5-%-Hard-Stop vollständig unverändert;
- der Stop kann nur nach oben, niemals wieder nach unten verschoben werden.

Das ist ausdrücklich **nicht** der verworfene frühe SOL-Ratchet +5 % → +1 %.
Der neue Trigger entspricht grob mehr als fünf anfänglichen Risikoeinheiten und
greift erst nach einer außergewöhnlich großen Bewegung.

### Vorabdiagnose und Hypothese

Eine kausale 1m-Pfaddiagnose der erhaltenen V12.12-Trades – noch kein neuer
Backtest – fand bei +30 % Aktivierung und +5 % Boden nur zwei betroffene
Champion-Trades: einen späteren SOL-Gewinn von +4,44 USDT, der ungefähr auf
+3,66 USDT sinken würde, und einen BNB-Trade, der nach +41,4 % Zwischengewinn
noch −4,67 USDT am Hard-Stop verlor und ungefähr +3,63 USDT sichern könnte.
Keiner der +50-%-ROI-Gewinner hätte den späten Boden berührt. Die isolierte
Diagnose ergab ungefähr +7,52 USDT, ist wegen Slot-/Protection-Wechselwirkungen
aber keine Ergebnisprognose.

Falsifizierbare Hypothese: Eine sehr späte, pair-unabhängige Sicherung bereits
großer Champion-Bewegungen verhindert vollständige Trend-Roundtrips, ohne die
seltenen +50-%-Gewinner oder normale Marktbewegungen abzuschneiden.

### Vorab festgelegte Annahmekriterien

V12.15 wird nur übernommen, wenn der exakte Drei-Jahres-Lauf:

1. den vollständigen Audit besteht;
2. mehr als +288,646 USDT Gewinn beziehungsweise 538,646 USDT Endkapital
   erreicht;
3. Profit Factor mindestens 2,4833 erreicht;
4. geschlossenen Drawdown höchstens 10 % hält;
5. mindestens 22 % Kapitalzeit und höchstens 63 % Zeit ohne Position erreicht;
6. alle sechs Pairs positiv hält;
7. keine V12.12-ROI-Gewinnquelle erkennbar zerstört;
8. alle Paritäts-, Sicherheits-, Unit- und Governance-Tests besteht.

Tradezahl und Verlustzahl sind Diagnosewerte, keine alleinigen Pass-Kriterien.
Bei FAIL wird V12.15 dokumentiert und der aktive Stand auf V12.12
zurückgesetzt. Kein Kriterium wird nachträglich verändert und der Fingerabdruck
darf nicht erneut laufen.

## Abgeschlossenes Ergebnis und Promotion V12.15

Der einzige Lauf `20260822T125812Z-68ac18a2` verwendete Commit
`bcf384fed3297e771a5ce78e2880e14af77346f9`, Strategy-Hash
`3c5aaf823e16c1a2901c4861fcf6dbc21da4dd0f1314385d78be1f2de86c4a97`
und Fingerabdruck
`f1d6ff6bbb489e0526b41487e126e509a8f20e1a1b8b84345a3cbeda79a28549`.
Alle 24 Candle-Sätze waren vollständig, lücken- und duplikatfrei. Exakte
Strategy/Configs, keine unerwarteten Dateien, keine veränderten Inputs und keine
Kindprozesse wurden bestätigt. Der formale Audit bestand.

| Kennzahl | V12.12 Maßstab | V12.15 | Veränderung | Gate |
|---|---:|---:|---:|---|
| Endkapital | 538,646 | 545,409 | +6,763 USDT | PASS |
| Nettogewinn | 288,646 | 295,409 | +6,763 USDT | PASS |
| Profit Factor | 2,4833 | 2,5554 | +0,0721 | PASS |
| Trades | 122 | 122 | 0 | Diagnose |
| Gewinne / Verluste | 22 / 100 | 23 / 99 | +1 / −1 | Diagnose |
| geschlossener Max-Drawdown | 9,62 % | 8,19 % | −1,43 Punkte | PASS |
| Kapitalzeit | 23,61 % | 23,07 % | −0,54 Punkte | PASS |
| Zeit ohne Position | 61,25 % | 61,33 % | +0,08 Punkte | PASS |
| ROI-Exits | 7 / +280,212 | 8 / +320,210 | +1 / +39,998 | PASS |

Pair-Ergebnisse: XRP +106,760, BTC +81,359, ETH +50,164, DOGE +30,335, BNB
+22,784 und SOL +4,007 USDT. Alle sechs Pairs blieben positiv.

Der Ratchet löste genau dreimal aus:

- SOL 21.12.2023–03.01.2024: +5,003 % / +4,009 USDT;
- SOL 07.11.–09.12.2024: +5,003 % / +4,008 USDT;
- BNB 16.09.–10.10.2025: +5,001 % / +3,971 USDT.

Die zweite SOL-Auslösung und der zusätzliche XRP-ROI-Gewinner zeigen erneut die
nicht additive Wallet-Chronologie. Entscheidend ist deshalb das bestandene
Gesamtportfolio, nicht die vorherige Zwei-Trade-Diagnose.

Entscheidung: **V12.15 ist der neue aktive Paper-/Dry-run-Kandidat.** Es ist
keine Echtgeldfreigabe und kein Profitversprechen. Der laufende Bot darf nur
dieselbe Strategy-/Config-Logik laden. Nächster sinnvoller Schritt ist frische
Dry-run-Evidenz oder ein vorab festgelegtes, nicht identisches Validierungsfenster;
der exakte Drei-Jahres-Fingerabdruck ist dauerhaft gesperrt.

## Vorabregistrierter nächster Versuch: V12.16

Zeitpunkt der Festlegung: 22.08.2026, **vor jeder V12.16-Codeänderung und vor
jedem ADA-Strategieergebnis**.

V12.15 bleibt der feste Rückfallstand. V12.16 verändert genau eine große
Dimension: `ADA/USDT` wird als siebter Spot-Markt in die bereits vorhandene
Broad-Core-Gruppe aufgenommen. ADA erhält exakt dieselben Entry-, Exit-,
Stoploss-, Protection- und Stake-Regeln wie SOL/XRP/BNB/DOGE. Es gibt keinen
ADA-spezifischen Parameter, keinen Reclaim-Einstieg und keine nachträgliche
Optimierung. Wallet 250 USDT, Stake 80 USDT, maximal drei Positionen,
Gebührenannahme 0,2 % je Seite und 1m-Detail bleiben unverändert.

Auswahlgrund: ADA wurde vor Kenntnis eines ADA-Strategieergebnisses aus einer
öffentlichen Binance-Spot-Liquiditätsprüfung als reifer, liquider, nicht
gehebelter Nicht-Stablecoin gewählt. Neue Hype-Paare, Stablecoins sowie
gehebelte/Sonderprodukte wurden ausgeschlossen. Die Hypothese lautet: Ein
zusätzlicher liquider Markt schafft mehr unabhängige Einstiegschancen und nutzt
das Kapital häufiger, ohne die Qualität des bestehenden Sechs-Pair-Kerns zu
verschlechtern.

### Unveränderliche Annahmekriterien V12.16

V12.16 wird nur übernommen, wenn der einzige exakte Drei-Jahres-Lauf:

1. den formalen Audit mit genau 28 erwarteten Candle-Sätzen besteht;
2. mehr als 295,409 USDT Nettogewinn und mehr als 545,409 USDT Endkapital erzielt;
3. Profit Factor mindestens 2,5554 erreicht;
4. geschlossenen Drawdown höchstens 10 % hält;
5. mehr als 23,07 % Kapitalzeit und weniger als 61,33 % Zeit ohne Position erreicht;
6. alle sieben Pairs positiv hält;
7. den ursprünglichen Sechs-Pair-Kern zusammen nicht unter den V12.12-Gewinn
   von 288,646 USDT drückt;
8. die seltene ROI-Gewinnquelle sichtbar erhält;
9. alle Paritäts-, Sicherheits-, Unit- und Governance-Tests besteht.

Tradezahl und ADA-Einzelgewinn sind nur Diagnosewerte. Kein Gate wird nach
Kenntnis des Ergebnisses gelockert. Bei einem FAIL bleiben Ergebnis,
Fingerabdruck und Begründung dokumentiert; aktive Strategy, Config, UI und
Startskripte werden vollständig auf V12.15 zurückgesetzt. Derselbe
Fingerabdruck darf nie erneut ausgeführt werden.

## Abgeschlossenes Ergebnis V12.16 und Rückkehr auf V12.15

Der einzige Lauf `20260822T202801Z-699e3b83` verwendete Commit `4725766`,
Strategy-Hash `9ad6f3e96d0f440a8a9cf4029cb6f64b7f6b73aba6ab524310f192797c1b6acf`
und Fingerabdruck `5b791472759974c22f2b5dad4f426247c53c9643938deaa0b7c4c96344510f65`.
Der Audit bestand mit genau 28 Candle-Sätzen, ohne Lücken, Duplikate,
unerwartete Repo-Lesezugriffe oder Kindprozesse.

V12.16 erreichte 548,135 USDT Endkapital (+298,135), 122 Trades, Profit
Factor 2,5356, 11,84 % Drawdown, 24,37 % Kapitalzeit und 60,50 % Zeit ohne
Position. ADA war mit +27,809 USDT positiv. Dennoch wurde SOL mit −1,025 USDT
negativ und die ursprünglichen sechs Pairs fielen zusammen auf 270,326 USDT.
Damit scheiterten Profit-Factor-, Drawdown-, All-Pairs- und Kernschutz-Gate.

Entscheidung: **REJECT.** Die aktive Technik wurde exakt auf V12.15
zurückgeführt. Lehre: Ein positiver Zusatzmarkt kann im geteilten 250-USDT-
Wallet durch Slot-Verdrängung trotzdem den Kern verschlechtern. ADA nicht auf
demselben historischen Fenster weiteroptimieren. V12.15 bleibt der aktive
Paper-/Dry-run-Kandidat; keine Echtgeldfreigabe.
