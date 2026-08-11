"""ida_gate — Grounding-Gate für RAG-Antworten (fail-closed).

Prüft, ob eine Entwurfsantwort durch die tatsächlich abgerufenen Quellabschnitte
gedeckt ist, und blockiert im Zweifel. Siehe README.md.
"""

__version__ = "0.1.0"

BANDS = ("gedeckt", "schwach", "ungedeckt")
