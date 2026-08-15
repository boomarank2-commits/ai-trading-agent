from pathlib import Path
p=Path('runtime/testbot_backtest_api.py')
s=p.read_text(encoding='utf-8').replace('"rows_in_required_window": int(len(in_window)),','"rows_in_required_window": len(in_window),')
p.write_text(s,encoding='utf-8')
