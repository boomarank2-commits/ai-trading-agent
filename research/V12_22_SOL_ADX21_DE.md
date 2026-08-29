# V12.22 – SOL-Ausbrüche nur mit bestätigter 4h-Richtungsstärke

Stand: 24.08.2026

Experiment: `V12.22-SOL-ADX21`

Elternstand: `V12.20-SELECTIVE-PYRAMID-ELIGIBILITY`

Strategie: `CompressionBreakout250`, Version `V12.22`

Vor dem ersten V12.22-Finanzlauf registrierter SHA-256:

`f7aac4afe8204aa7ce28a4a2bbf1d3c579ff4f084effa8bbff1c78ad8e9d2caf`

Status: **BESSERER PAPER-CHALLENGER – KEIN CHAMPION UND KEIN ECHTGELD.**

## Ausgangslage

Der exakt reproduzierte V12.20-SOL-Einzeltest über drei Jahre endete bei
247,971 USDT: −2,029 USDT, 25 Trades, Profit-Faktor 0,97 und 15,68 Prozent
geschlossener Drawdown. Alle fünf Gewinner starteten bei einem 4h-ADX über 21;
mehrere Verlierer entstanden bei schwächerer Richtungsstärke.

Das bestehende `PAIR_PROFILES`-Objekt enthält für SOL bereits den historischen
Wert 21. Das vollständige strenge V12.7-SOL-Profil wurde jedoch verworfen, weil
seine Kombination aus ADX, Momentum, RSI, Persistenz, Volumen und
Ausbruchsstärke einen großen Gewinner entfernte. V12.22 darf dieses
Mehrfachprofil deshalb nicht wiederherstellen.

Ein vorgeschalteter kausaler Screen von 144 festen Donchian-, Slow-Breakout-,
Trend-Pullback-, Bollinger-, Ichimoku- und Panic-Bounce-Varianten fand für SOL,
LTC und BCH keinen Kandidaten, der Auswahljahre, separates Prüfjahr und höhere
Gebühren gleichzeitig bestand. Diese Familien werden in V12.22 nicht vermischt.

## Eine falsifizierbare Änderung

Nur für `SOL/USDT` muss beim unveränderten bestehenden Donchian-Einstieg gelten:

`adx_4h >= 21`

Unverändert bleiben insbesondere:

- alle Signale von BTC, ETH, XRP, BNB, DOGE, LINK, TRX, LTC und BCH;
- SOL-Momentum, RSI, Trendpersistenz, Volumen und Ausbruchsstärke;
- sämtliche Exits, 5,5-Prozent-Hard-Stop und später 30→5-Profit-Ratchet;
- V12.20-Pyramiding nur für BTC, ETH, LINK und TRX;
- 250 USDT Wallet, 80 USDT je Block, höchstens drei Blöcke;
- Spot, Long-only, 1x und 0,2 Prozent Gebühr je Orderseite.

## Vor dem Test festgelegte Entscheidungshürden

V12.22 darf nur als besserer Paper-Kandidat fortgesetzt werden, wenn alle
folgenden Bedingungen erfüllt sind:

1. SOL bleibt im exakten Dreijahres-Einzeltest aktiv und hat mindestens 15
   Trades.
2. SOL wird positiv, erreicht Profit-Faktor über 1,0 und unterschreitet den
   V12.20-Drawdown von 15,68 Prozent.
3. Der SOL-Kostenstress mit 0,3 Prozent Gebühr je Orderseite bleibt positiv.
4. Der gemeinsame Zehn-Paare-Test über dieselben Kerzen übertrifft V12.20 mit
   +279,5931 USDT und Profit-Faktor 2,0114, ohne dessen 16,07 Prozent Drawdown
   zu überschreiten.
5. Kein zuvor positives Paar wird durch Slotverschiebung negativ.
6. Datei-, Kausalitäts-, Strategie-, Risiko- und Dry-run-Verträge bleiben grün.

Wenn eine Hürde scheitert, wird V12.22 als fehlgeschlagen dokumentiert und der
exakte V12.20-Stand wiederhergestellt. Nach dem Ergebnis werden keine weiteren
SOL-Schwellen innerhalb dieser Version verändert.

## Ergebnisse nach der Vorregistrierung

Der Kontrolllauf reproduzierte V12.20 exakt mit −2,029 USDT, 25 Trades,
Profit-Faktor 0,97 und 15,68 Prozent Drawdown.

| SOL-Einzeltest | V12.20 | V12.22 | Änderung |
| --- | ---: | ---: | ---: |
| Gewinn | −2,029 USDT | +8,021 USDT | +10,050 USDT |
| Trades | 25 | 23 | −2 |
| Profit-Faktor | 0,97 | 1,16 | +0,19 |
| Drawdown | 15,68 % | 12,26 % | −3,42 Punkte |

Beim Kostenstress mit 0,3 Prozent Gebühr je Orderseite blieb SOL mit
+5,064 USDT und Profit-Faktor 1,10 positiv.

Im gemeinsamen Wallet konkurrierten anschließend alle zehn Paare auf denselben
Kerzen um ein einziges 250-USDT-Wallet und höchstens drei Blöcke:

| Gemeinsamer Systemtest | V12.20 | V12.22 | Änderung |
| --- | ---: | ---: | ---: |
| Endkapital | 529,5931 USDT | 530,7752 USDT | +1,1821 USDT |
| Nettogewinn | +279,5931 USDT | +280,7752 USDT | +1,1821 USDT |
| Trades | 135 | 136 | +1 |
| Profit-Faktor | 2,0114 | 2,0230 | +0,0116 |
| Drawdown | 16,07 % | 16,07 % | unverändert gerundet |

Alle vorher positiven Paarbeiträge blieben positiv. SOL verbesserte seinen
gemeinsamen Beitrag von −31,49 auf −26,78 USDT. LTC blieb bei −17,44 USDT und
BCH bei −4,31 USDT; diese beiden Schwächen sind ausdrücklich nicht gelöst.

Der direkte gesperrte Runner lud exakt die registrierte Strategie und verwendete
die vorhandenen Laptop-Kerzen nur lesend. Er erzeugte jedoch nicht das formale
UI-Dateizugriffsmanifest. Deshalb bleiben ein offizieller UI-Dateiaudit und
frische Paper-Forward-Evidenz offen. Der relative Finanztest rechtfertigt den
Paper-Challenger, aber weder eine Champion- noch eine Echtgeld-Promotion.

## Forschungsziel und Grenze

Das Nutzerziel lautet langfristig 250 → mindestens 500 USDT je Coin in drei
Jahren sowie mehr als +250 USDT im gemeinsamen 250-USDT-Wallet. V12.22 behauptet
nicht, dieses Ziel bereits zu erreichen. Die Hürde dient dazu, den nächsten
kleinen kausalen Fortschritt zu messen, ohne das bekannte Zeitfenster so lange
zu optimieren, bis zufällig eine schöne Zahl erscheint.
