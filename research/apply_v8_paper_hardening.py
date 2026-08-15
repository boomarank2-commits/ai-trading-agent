from pathlib import Path

repo = Path('.')

launcher = repo / 'runtime' / 'scripts' / 'start-testbot-24x7.ps1'
s = launcher.read_text(encoding='utf-8')
s = s.replace('tradesv3.dryrun.sqlite', 'tradesv8.dryrun.sqlite')
launcher.write_text(s, encoding='utf-8')

validator = repo / 'runtime' / 'validate_dryrun_config.py'
s = validator.read_text(encoding='utf-8')
s = s.replace('"db_url": "sqlite:///user_data/tradesv3.dryrun.sqlite",', '"db_url": "sqlite:///user_data/tradesv8.dryrun.sqlite",')
needle = '''    for key, expected in exact_values.items():\n        _exact(key, config.get(key), expected)\n'''
insert = '''    for key, expected in exact_values.items():\n        _exact(key, config.get(key), expected)\n    _exact("minimal_roi", config.get("minimal_roi"), {"0": 0.50})\n    _exact("trailing_stop", config.get("trailing_stop"), False)\n'''
if needle not in s:
    raise SystemExit('validator insertion point missing')
s = s.replace(needle, insert, 1)
validator.write_text(s, encoding='utf-8')

test_launcher = repo / 'tests' / 'runtime' / 'test_testbot_launcher.py'
s = test_launcher.read_text(encoding='utf-8').replace('tradesv3.dryrun.sqlite', 'tradesv8.dryrun.sqlite')
test_launcher.write_text(s, encoding='utf-8')

# The generic configuration validator test should explicitly reject drift in
# the V8 research-proven exit contract as well as the old capital safeguards.
test_validator = repo / 'tests' / 'runtime' / 'test_validate_dryrun_config.py'
s = test_validator.read_text(encoding='utf-8')
needle = '''        (("max_open_trades",), 4),\n'''
replacement = '''        (("max_open_trades",), 4),\n        (("minimal_roi",), {"0": 0.05}),\n        (("trailing_stop",), True),\n        (("db_url",), "sqlite:///user_data/tradesv3.dryrun.sqlite"),\n'''
if needle not in s:
    raise SystemExit('validator test insertion point missing')
s = s.replace(needle, replacement, 1)
test_validator.write_text(s, encoding='utf-8')
