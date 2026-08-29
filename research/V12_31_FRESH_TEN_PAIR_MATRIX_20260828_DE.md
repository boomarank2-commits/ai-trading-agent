# Neuer vollständiger Zehnerlauf vom 28.08.2026

Batch: `20260828T160332Z-0fa691d7`

Laptop-Commit: `b1b5a2c153d22e780759346d449839f37942312a`

Strategie: V12.31, SHA-256
`e13a324560a4941350edd30b53e69ed6286eeb77f2b31673a859c3144e8965d5`

Status: **10/10 vollständig, 0 technische Fehler.**

Der Lauf wurde zunächst in der UI irreführend als „Fertig 100 %“ angezeigt,
obwohl nur der jeweils aktuelle Einzelcoin fertig war. Der serverseitig
gespeicherte Batch lief korrekt weiter und endete um 18:32 Uhr mit zehn
unterschiedlichen Paaren. Die UI-Korrektur trennt künftig Einzelcoin- und
Gesamtfortschritt.

Wichtig: Dieser Lauf misst den auf dem Laptop noch vorhandenen V12.31-Stand.
Er ist neue pair-lokale Evidenz, aber nicht der aktuelle V12.33-Paperkandidat.
V12.33 unterscheidet sich durch `LTC = NO_TRADE`; alle übrigen V12.31-Routen
bleiben erhalten.

## Zehn getrennte 250-USDT-Szenarien

| Pair | P/L | Trades | PF | Max DD | Einordnung |
|---|---:|---:|---:|---:|---|
| BTC/USDT | +163,2747 USDT | 15 | 8,3091 | 2,89 % | stärkster Einzelcoin; Route bewahren |
| ETH/USDT | +136,0261 USDT | 44 | 2,3759 | 13,19 % | stark, aber Verlustpfade weiter beobachten |
| SOL/USDT | +9,8730 USDT | 24 | 1,2031 | 12,26 % | zu schwach; V12.40-Kombination separat geprüft und verworfen |
| XRP/USDT | +92,7326 USDT | 19 | 3,9522 | 7,18 % | aktive Route bewahren; V12.39-Momentum verworfen |
| BNB/USDT | +17,8208 USDT | 18 | 1,6608 | 5,87 % | positiv, aber geringe Wertschöpfung; alte BNB-Ideen nicht wiederholen |
| DOGE/USDT | +106,4754 USDT | 25 | 2,8018 | 6,45 % | Supertrend-Route bewahren |
| LINK/USDT | +62,7272 USDT | 30 | 1,6280 | 26,02 % | profitabel, aber höchster Drawdown; Exit-Risiko priorisieren |
| TRX/USDT | +15,2343 USDT | 5 | 2,5261 | 3,63 % | zu kleine Stichprobe; keine Aussage aus PF allein |
| LTC/USDT | −45,0149 USDT | 18 | 0,0000 | 18,01 % | bestätigt V12.33-Entscheidung `NO_TRADE` |
| BCH/USDT | +18,4306 USDT | 20 | 1,3884 | 11,21 % | positiv, aber unter dem älteren +25-USDT-Gate |

Die arithmetische Summe der zehn voneinander unabhängigen Testwallets ist
**+577,5798 USDT bei 218 Trades**. Diese Summe ist kein Portfolioergebnis:
Jeder Coin startete separat mit 250 USDT. Für den realen Paperbot bleibt nur
der bereits exakt getestete gemeinsame 250-USDT-/3x80-Verlauf aussagekräftig.

## Pair-lokale nächste Schritte ohne Doppeltests

- BTC: bestehende starke Route nicht auf dem betrachteten Fenster retunen;
  frische Paper-Forward-Evidenz sammeln.
- ETH: bestehenden Gewinnpfad bewahren; eine neue Exit-Hypothese darf erst
  aus älteren, getrennten Verlustclustern vorregistriert werden.
- SOL: Range-Reversion, Supertrend allein, SOL-NO-TRADE und die feste
  Donchian/Supertrend-Kombination sind entschieden. Nur eine materiell andere
  Familie oder Forward-Evidenz ist zulässig.
- XRP: die 7-Tage-Momentum-Route V12.39 nicht wiederholen. Der aktive
  Donchian-Pfad bleibt der klare Vergleich.
- BNB: Compression-Release und Donchian80 sind verworfen; keine
  Schwellen-Nachjustierung dieser Familien.
- DOGE: den bestätigten Supertrend(20,3)-Pfad unverändert lassen.
- LINK: Keltner als Ersatz ist verworfen. Nächste Forschung muss eine
  eigenständige, auf älteren Daten entwickelte Drawdown-/Exit-Hypothese sein.
- TRX: TRX40 war isoliert positiv, verschlechterte aber das gemeinsame Wallet;
  der strikte Squeeze-Screen war zeitlich nicht robust. Nicht kombinieren.
- LTC: V12.33 bleibt `NO_TRADE`; EMA30/80 und Exhaustion-Reversion sind
  entschieden und dürfen nicht nachgetunt werden.
- BCH: die EMA30/80-Route bleibt aktiv; Adaptive-Supertrend war nicht robust.

## Forschungsregel

Das Ziel +250 USDT je Coin bleibt ein Suchziel, aber keine Erlaubnis, dieselbe
Dreijahreshistorie so lange nachzujustieren, bis sie die Zielzahl zeigt. Ein
neuer Lauf braucht einen neuen materiellen Fingerabdruck, eine vorab
dokumentierte Hypothese und getrennte Zeit-/Kostenhürden. Jeder neue
Einzelbericht zeigt künftig nur die Historie seines Coins sowie Änderung,
Ergebnis, Entscheidung, Erkenntnis und nächsten zulässigen Versuch.
