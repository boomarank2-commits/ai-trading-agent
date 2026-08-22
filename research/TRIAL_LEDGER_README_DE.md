# Trial Ledger

Das Trial Ledger ist verbindlicher Bestandteil des aktuellen Research-Masterplans. Es ist absichtlich **nicht** nur eine Gewinnerliste: negative, abgebrochene und pausierte Experimente bleiben sichtbar, damit Multiple Testing und Selection Bias später nicht unterschätzt werden.

Die aktuelle aktive Arbeitsgrundlage ist `RESEARCH_MASTERPLAN_DE.md`.

## Pflichtfelder

Neue Experimente müssen mindestens diese Felder pflegen:

- `experiment_id`
- `parent_experiment_id`
- `strategy_version`
- `strategy_hash`
- `parameter_hash`
- `hypothesis`
- `status`
- `date_decided`
- `development_window`
- `validation_window`
- `holdout_window`
- `pairs`
- `fees`
- `trade_count`
- `net_return`
- `profit_factor`
- `sharpe`
- `max_drawdown`
- `reason_accepted_or_rejected`
- `notes`
- `change_summary`
- `acceptance_criteria`
- `result_summary`
- `decision`
- `lessons`
- `next_experiment`

Leere Messwerte sind für Experimente erlaubt, die noch nicht gelaufen sind.
Identität, Hypothese, Status, Entscheidungsdatum und die sechs Felder der
Experimentkette dürfen nicht fehlen. Sobald eine exakte Strategy-Quelle gebaut
ist, gehört ihr SHA256 genau zu **einem** Experiment.

## Schutz vor Testschleifen

Vor jedem UI-Backtest wird ein inhaltlicher Fingerabdruck aus normalisierter
Strategy-Logik, sicherheitsrelevanter Konfiguration, Pair, Zeitraum und dem
festen Backtest-Protokoll gebildet. Kommentare, Docstrings und eine bloß geänderte
`STRATEGY_VERSION` zählen nicht als neue Logik. Ist der Fingerabdruck bereits in
einem erhaltenen ZIP vorhanden, wird der Lauf vor Datendownload und vor Anlage
eines neuen Run-Ordners blockiert. Es gibt im UI keinen Überschreiben-Schalter.

Ein echter neuer Versuch benötigt vor dem Lauf Vorgänger, isolierte Hypothese,
genaue Änderung, Erfolgskriterium und den Hash der fertigen Strategy-Quelle.
Nach dem Lauf werden Ergebnis, Entscheidung, Lehre und nächster Schritt ergänzt.
Jeder neue Run bewahrt `experiment-plan.json`, `strategy-change.diff` und
`experiment-result.json` im Run-Ordner und zusätzlich im Ergebnis-ZIP.

## V8-Sonderregeln

`V8-B0` bleibt der eingefrorene Champion mit LF-SHA256:

`9717526bac022404c0352f8d3681b76d8d793328303bcabe88db82aca4a10280`

Die vorregistrierte globale Volume-Serie besteht nur aus:

- B1: `volume_ratio >= 1.00`
- B2: `volume_ratio >= 1.25`

Nach Sicht auf B1/B2 wird keine neue Schwelle spontan ergänzt. B1 ist als globaler Filter verworfen; B2 ist bis nach Replay-/Diagnose-Gates pausiert.

## PBO / DSR

`runtime/statistical_audit.py` erwartet für PBO/DSR zusätzlich periodische Return-Serien aller vergleichbaren Varianten. Wenn frühere Versuche nicht vollständig rekonstruierbar sind, muss der statistische Audit das Trial-Universum ausdrücklich als unvollständig kennzeichnen.

PBO und Deflated Sharpe sind Research-Diagnostik und keine Echtgeldfreigabe.

## Lauf-Fingerabdrücke

`executed_test_fingerprints.csv` enthält jeden bereits ausgeführten materiellen
Test-Fingerabdruck, auch wenn der Lauf nach der Simulation an einem technischen
Audit-Gate scheiterte. Dadurch bleibt derselbe Strategy-/Config-/Pair-/Zeitraum-
Test nach einem Git-Pull oder in einem zweiten Arbeitsordner gesperrt. Rohdaten
und vollständige Resultat-ZIPs bleiben weiterhin lokal außerhalb von Git.

## Automatischer Governance-Check

```bat
.\.venv\Scripts\python.exe runtime\research_governance.py
```

Der Check prüft unter anderem Masterplan, V8-Freeze, Ledger-Schema,
Parent-Referenzen, eindeutige Strategy-Hashes, die exakten V12.12- bis V12.16-Registrierungen und
die vorregistrierten Volume-Schwellen.
