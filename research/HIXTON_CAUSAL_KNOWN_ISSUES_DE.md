# Hixton Causal Analysis – bekannte Punkte

## Batch-Header des abgeschlossenen Diagnose-Laufs

Der vollständige Diagnose-Lauf vom 30.08.2026 wurde technisch mit

- Experiment `HIXTON-V1-TRADE-DIAGNOSTICS`
- Strategie `HIXTON-V1-DIAG`
- SHA256 `d43da032ad8aac714da60027702f84b584fc9cbc7e84038ca06847b5c2342290`

ausgeführt. Die einzelnen `experiment-result.json`-Dateien enthalten diese Identität korrekt.

Der übergeordnete Batch-Plan/Batch-Header wurde jedoch noch mit den alten Adapter-Konstanten `HIXTON-V1-ORIGINAL-BASELINE` / `HIXTON-V1` beschriftet.

Bewertung: **Metadaten-/Beschriftungsfehler, kein Tradingfehler.**

Die Causal-Analyzer dürfen den Batch-Header deshalb nicht als primäre Identität verwenden. Sie selektieren die Runs anhand der einzelnen Experiment-ID und des exakten Strategie-SHA256.

Vor einem zukünftigen neuen Backtest-Batch müssen die Adapter-Konstanten korrigiert werden. Für die jetzige Offline-Ursachenanalyse ist kein erneuter V1-Lauf erforderlich.
