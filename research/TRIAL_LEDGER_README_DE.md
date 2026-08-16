# Trial Ledger

Das Ledger ist absichtlich append-or-update statt "nur Gewinner". Negative und abgebrochene Experimente bleiben sichtbar, damit Multiple Testing und Selection Bias später nicht unterschätzt werden.

Pflichtfelder für neue Experimente sind mindestens Experiment-ID, Parent, Strategie-/Config-Hash, vorab formulierte Hypothese, Datenfenster, Pairs, Kosten, Tradezahl, Nettoergebnis, Profit Factor, Drawdown und eine begründete Entscheidung.

`runtime/statistical_audit.py` erwartet für PBO/DSR zusätzlich periodische Return-Serien aller vergleichbaren Varianten. Wenn frühere Versuche nicht vollständig rekonstruierbar sind, muss der statistische Audit das Trial-Universum ausdrücklich als unvollständig kennzeichnen.
