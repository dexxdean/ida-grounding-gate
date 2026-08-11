"""Datenklassen für die Grounding-Pipeline.

Bewusst schlank und ohne externe Abhängigkeiten (nur stdlib), damit das Kernpaket
überall im BRZ-Umfeld ohne Installationsaufwand läuft.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class FAQItem:
    """Ein Frage→Antwort→Quelle-Tripel aus der öffentlichen gov.at-Wissensbasis.

    Das ist die Ground Truth, gegen die geprüft wird. `stand` hält das
    Redaktions-/Abrufdatum fest — zentral gegen den „2024-Daten"-Fehlertyp.
    """

    frage: str
    antwort: str
    quelle_url: str
    kategorie: str = ""
    stand: str = ""  # ISO-Datum, wann der Absatz abgerufen/gültig war
    ist_frage: bool = True  # True = echte Nutzerfrage; False = Abschnitts-Überschrift

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TestQuestion:
    """Eine Testfrage für die Evaluierung.

    `erwartet`:
      - "gedeckt"    : Antwort steht in der Wissensbasis → Gate soll durchlassen
      - "ungedeckt"  : Falle (z. B. „Wer ist Außenministerin?") → Gate soll blocken
    """

    frage: str
    erwartet: str  # "gedeckt" | "ungedeckt"
    notiz: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GroundingResult:
    """Ergebnis einer Gate-Prüfung einer Entwurfsantwort gegen Quellabschnitte."""

    band: str  # "gedeckt" | "schwach" | "ungedeckt"
    score: float  # 0..1 Deckungsgrad (1 = voll gedeckt)
    allow: bool  # True = ausliefern, False = blockieren
    claims: list[dict[str, Any]] = field(default_factory=list)  # je Aussage: text, gedeckt, quelle
    reason: str = ""
    judge: str = ""  # welcher Prüfer entschied ("heuristik" | "mistral")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditEvent:
    """Ein Protokolleintrag — angelehnt an drift_limiter/store.py.

    Jede Ausgabe- oder Block-Entscheidung wird hiermit nachvollziehbar.
    """

    kind: str  # "gate_check"
    frage: str
    band: str
    allow: bool
    judge: str
    sources: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
