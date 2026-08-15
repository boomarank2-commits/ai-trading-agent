from pathlib import Path

path = Path('tests/runtime/test_runtime_contract.py')
s = path.read_text(encoding='utf-8')
old = '''        self.assertNotIn("iloc[-1]", self.source.replace(" ", ""))\n        self.assertNotIn("iat[-1]", self.source.replace(" ", ""))\n'''
new = '''        # Last-row access is legitimate inside post-fill callbacks such as\n        # order_filled(), where Freqtrade exposes only information available at\n        # that callback time. Keep the strict prohibition where signals and\n        # indicators are generated, because there it could leak the dataframe's\n        # future endpoint into historical rows.\n        causal_signal_methods = {\n            "populate_indicators",\n            "populate_indicators_1h",\n            "populate_indicators_4h",\n            "populate_indicators_btc_4h",\n            "populate_entry_trend",\n            "populate_exit_trend",\n        }\n        for node in self.strategy.body:\n            if not isinstance(node, ast.FunctionDef) or node.name not in causal_signal_methods:\n                continue\n            method_source = ast.get_source_segment(self.source, node) or ""\n            compact = method_source.replace(" ", "")\n            self.assertNotIn("iloc[-1]", compact, node.name)\n            self.assertNotIn("iat[-1]", compact, node.name)\n'''
if old not in s:
    raise SystemExit('expected blanket iloc assertions not found')
s = s.replace(old, new, 1)
path.write_text(s, encoding='utf-8')
