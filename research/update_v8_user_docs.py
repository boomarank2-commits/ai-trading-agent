from pathlib import Path

p = Path('TESTBOT_ANLEITUNG.md')
s = p.read_text(encoding='utf-8')
s = s.replace(
    '- `tradesv3.dryrun.sqlite`: persistente Freqtrade-Datenbank aller simulierten\n  Trades;',
    '- `tradesv8.dryrun.sqlite`: eigene persistente Freqtrade-Datenbank des V8-Paper-Forward-Tests. Alte V2/V3-Datenbanken bleiben getrennt erhalten und werden nicht in die V8-Auswertung gemischt;',
)
old = '''Die vorhandene Strategie war in den bisherigen historischen Prüfungen negativ.\nDieser Dry-run dient dazu, Funktion, Stabilität und Verhalten zu beobachten.\nWeder ein mehrtägiger Lauf noch ein zwischenzeitliches Plus beweist eine\nprofitable Strategie oder rechtfertigt Echtgeldbetrieb. Der Bot ist damit\nweder als identische Kopie des Videos noch als produktionsreifer Handelsbot\nausgewiesen.'''
new = '''Der aktuelle V8-Kandidat ist eine langsame 4h-Donchian-Trendstrategie und wurde\nvor dem Paper-Start deutlich breiter geprüft als die verworfenen V1–V7-Varianten.\nUnter dem konservativen historischen Kostenproxy blieb das gemeinsame\nBTC/ETH/SOL-Portfolio unter anderem im Drei-Jahres-, älteren Holdout- und\nFünf-Jahres-Test positiv. Die Detailzahlen und Gegenbeispiele stehen in\n`docs/V8_PAPER_CANDIDATE_REPORT_DE.md`.\n\nDas ist trotzdem **kein Profitversprechen**. Die Strategie besitzt eine niedrige\nTrefferquote, kann lange Verlustserien haben und war in einzelnen historischen\nJahresslices negativ. Wenige große Trends tragen einen wesentlichen Teil des\nErtrags. Genau deshalb startet V8 in einer frischen `tradesv8.dryrun.sqlite` und\nmuss zuerst unverändert im Paper-Forward-Test bestehen. Ein mehrtägiges Plus,\nein einzelner großer Gewinner oder ein guter Backtest rechtfertigt weiterhin\nkeinen Echtgeldbetrieb.'''
if old not in s:
    raise SystemExit('old strategy-status paragraph not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

p = Path('STARTBOT.bat')
s = p.read_text(encoding='utf-8').replace('\n echo nicht zulaessig.\n', '\necho nicht zulaessig.\n')
p.write_text(s, encoding='utf-8')
