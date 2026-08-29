# Fester Parabolic-SAR-Transfer – Kapitaleffizienz-Screen

Stand: 29.08.2026

## Vorab festgelegte Route

Als sachlich andere Trendfamilie wurde genau eine feste 4h-Route ohne
Parametersuche auf SOL, BNB, TRX, LTC, BCH und LINK geprüft:

- TA-Lib Parabolic SAR mit `acceleration=0.02` und `maximum=0.20`;
- Long beim ersten 4h-Schlusskreuz über den PSAR;
- nur oberhalb einer seit zwölf 4h-Kerzen steigenden EMA200;
- Exit beim Schlusskreuz unter den PSAR;
- unverändert 80 USDT, ein Block, −5,5 % Hard-Stop, 50 % ROI;
- 0,2 % Gebühr je Seite und zusätzlicher 0,3-%-Kostenstress;
- Ausführung im Screen konservativ am nächsten 4h-Open.

Der Screen nutzte drei getrennte Jahresfalten vom 30.08.2023 bis 29.08.2026.
Dieses Gesamtfenster ist aus anderen Strategieversuchen bereits bekannt und
deshalb kein frischer Holdout. Der Zweck war nur, einen ungeeigneten
Mechanismus vor einem teuren exakten Freqtrade-Kandidaten auszusortieren.

Die feste Öffnungshürde verlangte mindestens zwei positive Jahresfalten, ein
positives jüngstes Jahr, mindestens +25 USDT und 15 Trades, PF mindestens 1,30,
mindestens 1,00 USDT Gewinn je 100 USDT Entry-Kapital sowie positiven
Kostenstress mit mindestens +15 USDT und PF 1,20.

## Ergebnis

| Pair | P/L 0,2 % | Trades | PF | positive Jahre | USDT/100 Entry | 0,3-%-Stress | Exakt öffnen? |
|---|---:|---:|---:|---:|---:|---:|---|
| SOL | +40,63 | 127 | 1,18 | 3/3 | 0,40 | +20,25 | Nein |
| BNB | +4,75 | 140 | 1,03 | 2/3 | 0,04 | −17,64 | Nein |
| TRX | +63,75 | 157 | 1,57 | 3/3 | 0,51 | +38,53 | Nein |
| LTC | −97,93 | 108 | 0,52 | 0/3 | −1,13 | −115,00 | Nein |
| BCH | −85,37 | 108 | 0,61 | 0/3 | −0,99 | −102,46 | Nein |
| LINK | −72,47 | 118 | 0,71 | 0/3 | −0,77 | −91,18 | Nein |

## Bindende Entscheidung

Kein Pair öffnet einen exakten V12.45-Kandidaten. TRX und SOL waren zwar über
alle drei Jahre positiv, aber ihre vielen Entry-Fills erzeugten deutlich
weniger als 1 USDT Nettogewinn je 100 USDT Entry-Kapital; zudem verfehlte SOL
den PF-Boden. Mehr Aktivität ohne ausreichende Nettokante würde Gebühren und
Slotzeit erhöhen, nicht das Nutzerziel erfüllen.

Die PSAR-Nachbarschaft `0.02/0.20` plus steigende EMA200 darf auf diesem
Fenster nicht pair-lokal nachgestimmt werden. Der aktive V12.33-Code und sein
Hash bleiben unverändert. Es wurde kein exakter Einzel-, Kosten- oder
Shared-Wallet-Lauf geöffnet.

## Modellgrenze

Der Screen simuliert weder Freqtrade-Protektionen noch 1m-Detail, Limit-Fills,
Pyramiding oder gemeinsame 3×80-USDT-Slotkonkurrenz. Ein positives Ergebnis
wäre nur die Erlaubnis zum exakten Kandidaten gewesen, kein Beweis. Die
technische Indikatorfunktion ist in der offiziellen
[TA-Lib-Python-Dokumentation](https://ta-lib.github.io/ta-lib-python/func_groups/overlap_studies.html)
beschrieben.
