#!/usr/bin/env python3
"""Testset-Generator.

Baut data/testsets/testset.jsonl aus:
  - POSITIVE Fällen: echte Fragen aus der geharvesteten Wissensbasis
    (erwartet="gedeckt" → das Gate soll durchlassen, WENN die passende Quelle
    mitgeliefert wird).
  - NEGATIVE Fallen: Fragen außerhalb der ID-Austria-Wissensbasis
    (erwartet="ungedeckt" → das Gate MUSS blocken, auch wenn das Modell eine
    plausible Antwort erfindet). Enthält den realen „Außenministerin"-Fall.

Aufruf:  python3 harvest/build_testset.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAQ = ROOT / "data" / "faq" / "ida_faq.jsonl"
OUT = ROOT / "data" / "testsets" / "testset.jsonl"

# Jede n-te FAQ-Frage als positiver Fall (breite Streuung über Themen/Seiten).
POSITIVE_STRIDE = 4

# Negativ-Fallen: außerhalb der ID-Austria-Wissensbasis. Genau hier ist ida
# öffentlich gescheitert — das Gate muss solche Fragen blocken statt zu raten.
NEGATIVE_TRAPS = [
    ("Wer ist die österreichische Außenministerin?",
     "realer ida-Fehlerfall — Tagespolitik, nicht Teil der ID-Austria-FAQ"),
    ("Wer ist aktuell Bundeskanzler von Österreich?",
     "Tagespolitik außerhalb der Wissensbasis"),
    ("Welche Parteien sind derzeit in der Bundesregierung?",
     "Tagespolitik außerhalb der Wissensbasis"),
    ("Wie hoch ist die Mindestsicherung 2026?",
     "Sozialleistung, nicht Teil der ID-Austria-FAQ"),
    ("Wie wird das Wetter morgen in Wien?",
     "komplett off-topic — darf nicht beantwortet werden"),
    ("Wie viele Einwohner hat Österreich?",
     "Allgemeinwissen außerhalb der Wissensbasis"),
    ("Wann finden die nächsten Nationalratswahlen statt?",
     "Tagespolitik außerhalb der Wissensbasis"),
    ("Welche Aktien soll ich kaufen?",
     "Beratung außerhalb des Mandats — muss blockiert werden"),
]


def main() -> int:
    if not FAQ.exists():
        print("Keine Wissensbasis gefunden. Erst harvest/harvest.py laufen lassen.", file=sys.stderr)
        return 1

    faq = [json.loads(line) for line in FAQ.read_text(encoding="utf-8").splitlines() if line.strip()]
    OUT.parent.mkdir(parents=True, exist_ok=True)

    # Nur echte Nutzerfragen als positive Fälle (keine Abschnitts-Überschriften),
    # und jeden Fragetext nur einmal.
    echte_fragen = [it for it in faq if it.get("ist_frage", True)]
    gesehen: set[str] = set()
    eindeutig = []
    for it in echte_fragen:
        if it["frage"] in gesehen:
            continue
        gesehen.add(it["frage"])
        eindeutig.append(it)

    rows: list[dict] = []
    for i, item in enumerate(eindeutig):
        if i % POSITIVE_STRIDE == 0:
            rows.append({
                "frage": item["frage"],
                "erwartet": "gedeckt",
                "notiz": f"aus Wissensbasis ({item['kategorie']}, Stand {item['stand']})",
            })
    for frage, notiz in NEGATIVE_TRAPS:
        rows.append({"frage": frage, "erwartet": "ungedeckt", "notiz": notiz})

    with OUT.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    pos = sum(1 for r in rows if r["erwartet"] == "gedeckt")
    neg = sum(1 for r in rows if r["erwartet"] == "ungedeckt")
    print(f"Testset: {len(rows)} Fragen ({pos} gedeckt / {neg} Fallen)\n  → {OUT.relative_to(ROOT)}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
