#!/usr/bin/env python3
"""Bereinigung + Klassifikation der geharvesteten FAQ-Rohdaten.

Transparente, dokumentierte Regeln (alle aus einem Audit der echten Daten
abgeleitet, siehe harvest/README.md → Abschnitt „Bereinigung"):

TEXT-NORMALISIERUNG (auf Frage und Antwort):
  N1  Leerzeichen-Artefakte aus leeren Inline-Tags: "SMS - TAN" → "SMS-TAN",
      "FIDO -Schlüssel" → "FIDO-Schlüssel", "E -Mail" → "E-Mail".
  N2  Leerzeichen vor Satzzeichen entfernen: "App ?" → "App?",
      "Service Center ." → "Service Center.".
  N3  Leerzeichen innerhalb typografischer Anführungszeichen: „ ID → „ID.
  N4  Domain-Tippfehler der Quelle: "osterreich.gv.at" → "oesterreich.gv.at".
  N5  Mehrfach-Leerzeichen auf eines reduzieren, trimmen.

ENTFERNEN (kein Wissenswert):
  D1  Reine Kontakt-CTA-Blöcke (Antwort == "Bitte kontaktieren Sie das
      Service Center.") — Struktur-Element, keine ID-Austria-Info.
  D2  Exakte Duplikate (gleiche Frage UND Antwort) — erstes Vorkommen bleibt.

KLASSIFIKATION:
  ist_frage = True nur, wenn der Titel eine echte Nutzerfrage ist
    (endet auf "?" UND kein generisches Struktur-Heading).
  Abschnitts-Überschriften bleiben als Wissensbasis erhalten (ist_frage=False),
  werden aber NICHT als positive Testfragen verwendet.

Aufruf:  python3 harvest/clean.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAQ_DIR = ROOT / "data" / "faq"
SRC = FAQ_DIR / "ida_faq.jsonl"

# Generische Struktur-Headings: enden auf "?", sind aber keine echten Fragen.
GENERIC_HEADINGS = {
    "Wann hilft mir diese Anleitung?",
    "Brauchen Sie weitere Unterstützung?",
}
# Antworten ohne Wissenswert (reine CTA).
DROP_ANSWERS = {
    "Bitte kontaktieren Sie das Service Center.",
}

_SPACED_HYPHEN = re.compile(r"(\w)\s+-\s*(\w)")            # N1
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([?!.,;:])")          # N2
_QUOTE_OPEN = re.compile(r"„\s+")                            # N3
_QUOTE_CLOSE = re.compile(r"\s+“")                           # N3
_WS = re.compile(r"\s+")                                     # N5


def normalize_text(text: str) -> str:
    text = _SPACED_HYPHEN.sub(r"\1-\2", text)
    text = _SPACE_BEFORE_PUNCT.sub(r"\1", text)
    text = _QUOTE_OPEN.sub("„", text)
    text = _QUOTE_CLOSE.sub("“", text)
    text = text.replace("osterreich.gv.at", "oesterreich.gv.at")  # N4
    text = _WS.sub(" ", text).strip()                             # N5
    return text


def is_question(frage: str) -> bool:
    return frage.rstrip().endswith("?") and frage not in GENERIC_HEADINGS


def clean_items(items: list[dict]) -> tuple[list[dict], dict]:
    report = {"eingang": len(items), "cta_entfernt": 0, "duplikate_entfernt": 0,
              "fragen": 0, "abschnitte": 0}
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for it in items:
        frage = normalize_text(it["frage"])
        antwort = normalize_text(it["antwort"])
        if antwort in DROP_ANSWERS:                       # D1
            report["cta_entfernt"] += 1
            continue
        key = (frage, antwort)
        if key in seen:                                   # D2
            report["duplikate_entfernt"] += 1
            continue
        seen.add(key)
        frage_flag = is_question(frage)
        out.append({
            "frage": frage,
            "antwort": antwort,
            "quelle_url": it["quelle_url"],
            "kategorie": it["kategorie"],
            "stand": it["stand"],
            "ist_frage": frage_flag,
        })
        report["fragen" if frage_flag else "abschnitte"] += 1
    report["ausgang"] = len(out)
    return out, report


def _write(items: list[dict]) -> None:
    fields = ["frage", "antwort", "quelle_url", "kategorie", "stand", "ist_frage"]
    with (FAQ_DIR / "ida_faq.jsonl").open("w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    with (FAQ_DIR / "ida_faq.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(items)


def main() -> int:
    if not SRC.exists():
        print("Keine Rohdaten. Erst harvest/harvest.py laufen lassen.", file=sys.stderr)
        return 1
    items = [json.loads(line) for line in SRC.read_text(encoding="utf-8").splitlines() if line.strip()]

    # Rohfassung sichern (einmalig), bevor überschrieben wird.
    backup = FAQ_DIR / "ida_faq.raw.jsonl"
    if not backup.exists():
        backup.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")

    cleaned, report = clean_items(items)
    _write(cleaned)
    print("Bereinigung:", json.dumps(report, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
