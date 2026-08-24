# Kompaktes Versuchsregister: Lehren und Sperren

Die vollstaendige maschinenlesbare Kette steht in research/trial_ledger.csv.
Diese Datei ist die menschlich lesbare Sperrliste fuer Deep Research.

## Globale Lehren

- Ein globaler Volumenfilter half BTC, machte ETH/SOL aber zu duenn. Nur
  pair-lokale Evidenz ist zulaessig.
- Mehr kurzfristige Entries erzeugten sehr viele Trades, aber negative
  Erwartung nach Kosten. Aktivitaet allein ist kein Ziel.
- ORB, Ichimoku und Bollinger wurden in V11 gemeinsam und unzureichend
  verdrahtet verworfen. Das widerlegt nicht sauber definierte, getrennte
  Standalone-Challenger; es verbietet nur denselben Mischversuch.
- Gestaffelte Gewinnmitnahmen schnitten die seltenen grossen Trendgewinner ab.
  V12.5 bestaetigte, dass diese Gewinner fuer den Breakout-Erwartungswert
  wesentlich sind.
- Ein frueher SOL-Profit-Ratchet schnitt Gewinner ab. Nicht wiederholen.
- Eine erste Verlustsperre fuer alle Paare reduzierte Chancen und
  verschlechterte das Portfolio. Nicht global verschaerfen.
- Ein spaeter Champion-Ratchet erst ab +30 Prozent mit +5-Prozent-Boden war
  erfolgreich. Er gilt nur fuer passende Champion-Donchian-Tags.
- Zusaetzliche Bloecke sind nur bei BTC, ETH, LINK und TRX erlaubt. Eine
  Freigabe fuer andere Coins benoetigt neue pair-lokale Evidenz.
- Eine positive neue Coin-Route kann wertvollere Signale verdraengen. Der
  gemeinsame 250-USDT-Systemlauf ist immer bindend.

## Nicht erneut auf demselben Fenster optimieren

- BTC/ETH/SOL: V12.10 48h/24h-Continuation und V12.11 EMA50-Reclaim.
- ETH: blosses Entfernen des negativen Reclaim-Pfads. V12.13 verschlechterte
  wegen geaenderter Protection- und Slotchronologie den gemeinsamen Lauf.
- SOL: alter +5-auf-+1-Profit-Ratchet; die verworfene zusammengesetzte
  V12.7-Filterkombination; RSI30-auf-50 ueber steigender EMA200 samt
  benachbarten Schwellen.
- LTC: RSI30-auf-50 ueber steigender EMA100; EMA30/EMA80 ueber steigender
  EMA200 bei ADX12; Empty-Portfolio-Slotregel; dieselbe Route in V12.31.
- TRX: Donchian40/40 ueber steigender EMA200, mit oder ohne Pyramiding.
- BNB: Donchian80/20 ueber steigender EMA200 und positivem 30-Tage-Momentum.
- BCH: EMA30/EMA80 ueber steigender EMA100 bei ADX24 nicht nachstimmen. Sie ist
  bereits unveraendert in V12.31 angenommen.
- DOGE: Supertrend(20,3) ueber steigender EMA100 nicht nachstimmen. Sie ist
  bereits angenommen.
- ADA: unveraenderte Broad-Core-Uebertragung. ADA war positiv, verschlechterte
  aber das gemeinsame Portfolio und gehoert nicht zu den zehn aktiven Coins.

## Versionskette ab der Zehn-Paare-Erweiterung

| Version | Hauptversuch | Urteil |
| --- | --- | --- |
| V12.17 | zehn Paare und mehrere Bloecke ohne vollstaendigen Gewinnguard | technisch/konzeptionell verworfen |
| V12.18 | Profit-only und hoeherer Einstieg fuer Zusatzbloecke | technische Reparatur |
| V12.20 | Pyramiding nur BTC/ETH/LINK/TRX | als Zehn-Paare-Paperbasis behalten |
| V12.21 | pair-lokaler Volumenversuch | verworfen |
| V12.22 | SOL zusaetzlich ADX >= 21 | angenommen |
| V12.23 | LTC EMA30/80 allein positiv | gemeinsames Wallet schlechter, verworfen |
| V12.24 | LTC nur bei leerem Portfolio | noch schlechter, verworfen |
| V12.25 | BCH EMA-Route falsch verdrahtet | technischer Abbruch, kein Finanzergebnis |
| V12.26 | BCH-Route technisch korrigiert | allein gut, damaliges DD-Gate knapp verfehlt |
| V12.27 | TRX40 mit geerbtem Pyramiding | DD zu hoch, verworfen |
| V12.28 | TRX40 als Einzelblock | allein stark, gemeinsames Wallet schlechter |
| V12.29 | BNB Donchian80 | festes Einzelgewinn-Gate knapp verfehlt |
| V12.30 | DOGE Supertrend20x3 | angenommen |
| V12.31 | feste DOGE- und BCH-Routen kombiniert | aktive Paper-/Dry-run-Basis |
| V12.32 | feste LTC-Route in V12.31 kombiniert | gemeinsamer Gewinn minus 50,035, verworfen |

## Was als sachlich neuer Versuch gilt

Eine andere, vorab begruendete Routenfamilie; ein anderer kausaler
Marktmechanismus; neue unverbrauchte Daten; oder eine reine Diagnose ohne
Tradingentscheidung. Eine benachbarte Schwelle, ein nach Ergebnis gewaehlt
engerer Stop oder ein anders formulierter Slotfilter ist kein neuer Versuch.
