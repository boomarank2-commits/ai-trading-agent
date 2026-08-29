# Deep-Research-Uebergabe fuer zehn Kryptowaehrungen

Stand: 24.08.2026

Diese Mappe ist der Einstieg fuer eine neue GPT-Deep-Research-Auswertung. Sie
behandelt BTC, ETH, SOL, XRP, BNB, DOGE, LINK, TRX, LTC und BCH als zehn
getrennte Forschungsobjekte. Eine gute Regel bei einem Coin wird nicht ohne
eigenen Nachweis auf einen anderen Coin uebertragen.

## In dieser Reihenfolge lesen

1. MASTERPROMPT_DE.md
2. EVIDENZMATRIX_DE.md
3. PRUEFPROTOKOLL_DE.md
4. VERSUCHSREGISTER_NICHT_WIEDERHOLEN_DE.md
5. das jeweilige Dossier unter coins/
6. research/trial_ledger.csv und die dort referenzierten Versionsberichte
7. die aktive Strategiequelle und die technischen Sicherheitsvertraege

## Wichtigster Ausgangspunkt

Der aktive Paper-/Dry-run-Kandidat ist CompressionBreakout250 V12.31 mit dem
SHA-256:

e13a324560a4941350edd30b53e69ed6286eeb77f2b31673a859c3144e8965d5

Der exakte gemeinsame Drei-Jahres-Test verwendete nur ein Wallet mit 250 USDT,
hoechstens drei gleichzeitig belegten 80-USDT-Bloecken und allen zehn Coins:

- Endkapital 669,857 USDT
- Gewinn +419,8571 USDT
- 155 Trades
- Profit-Faktor 2,4358
- geschlossener Drawdown 12,5447 Prozent

Das ist keine Summe von zehn Einzelwallets. Einzeltests starten dagegen jeder
mit eigenen 250 USDT und dienen der Paar-Diagnose. Eine isoliert profitable
Coin-Route kann den gemeinsamen Lauf durch Slotverdraengung verschlechtern.
V12.32 bewies das: LTC war allein profitabel, der gemeinsame Gewinn sank aber
um 50,035 USDT.

## Forschungsziel

Das Ziel 250 auf 500 USDT je Coin in drei Jahren ist eine ambitionierte
Forschungsrichtung, keine nachtraeglich zu erzwingende Abnahmegrenze und keine
Gewinngarantie. Deep Research soll fuer jeden Coin getrennt entscheiden:

- KEEP_CURRENT: vorhandene Route nur robust weiterpruefen;
- RESEARCH_NEW_FAMILY: eine sachlich neue, vorab registrierbare Hypothese;
- NO_TRADE_CANDIDATE: keine belastbare pair-lokale Kante gefunden.

Erst ein isolierter Test und danach der echte gemeinsame 3x80-USDT-Systemtest
koennen eine Aenderung fuer den Paperbot qualifizieren.

## Enthaltene Coin-Dossiers

- coins/BTC_DE.md
- coins/ETH_DE.md
- coins/SOL_DE.md
- coins/XRP_DE.md
- coins/BNB_DE.md
- coins/DOGE_DE.md
- coins/LINK_DE.md
- coins/TRX_DE.md
- coins/LTC_DE.md
- coins/BCH_DE.md

UPLOAD_MANIFEST_DE.md beschreibt, welche Originaldateien gemeinsam mit dieser
Mappe hochgeladen werden und welche privaten oder riesigen Laufartefakte
ausdruecklich ausgeschlossen bleiben.
