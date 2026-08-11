"""Das Grounding-Gate: Entwurfsantwort → Band (gedeckt/schwach/ungedeckt).

Zerlegt die Antwort in prüfbare Aussagen, lässt jede vom Judge gegen die
abgerufenen Quellen bewerten und aggregiert zu einem Band. Fail-closed:
ohne Quellen oder bei ungedeckten Aussagen wird blockiert.
"""

from __future__ import annotations

import re

from .judge import Judge, get_judge
from .models import GroundingResult

# Schwellen auf dem Deckungsgrad der schwächsten Aussage (0..1).
# Konservativ: eine einzige ungedeckte Aussage zieht das Band nach unten.
GEDECKT_MIN = 0.75
SCHWACH_MIN = 0.40


# Diskurs-Rahmung ohne eigenen Faktengehalt. Solche Wendungen leiten eine Antwort
# ein, behaupten aber selbst nichts Prüfbares — sie gegen Quellen zu benoten
# erzeugt nur Fehlblocks. Vor der Claim-Prüfung am Satzanfang entfernen.
# (Empirisch: „grundsätzlich/gilt/kurz/gesagt" waren die dominanten Token-Misses
#  bei fälschlich geblockten, korrekt paraphrasierten Antworten — siehe eval/.)
_RAHMEN_PHRASEN = (
    "kurz gesagt", "grundsätzlich gilt", "im wesentlichen", "im prinzip",
    "im grunde genommen", "im grunde", "in der regel", "generell gilt",
    "zusammengefasst", "zusammenfassend", "kurzum", "vereinfacht gesagt",
    "bitte beachten sie", "beachten sie bitte", "bitte beachten",
    "wichtiger hinweis", "hinweis", "achtung", "grundsätzlich", "generell",
)
# Einzelne einleitende Konnektoren: nur das Führungswort fällt weg, der Rest des
# Satzes bleibt als Aussage erhalten.
_KONNEKTOREN = frozenset({
    "außerdem", "zudem", "ergänzend", "übrigens", "ferner", "weiters",
    "weiterhin", "des weiteren", "darüber hinaus",
})


def _strip_framing(satz: str) -> str:
    """Entfernt eine führende Diskurs-Rahmung/Konnektor, behält die Aussage."""
    s = satz.strip()
    low = s.lower()
    for phrase in _RAHMEN_PHRASEN:
        if low.startswith(phrase):
            rest = s[len(phrase):].lstrip(" :,–-")
            # Nur strippen, wenn danach echter Satz folgt (nicht alles wegfällt).
            if len(rest) >= 3:
                s, low = rest, rest.lower()
            break
    for konn in _KONNEKTOREN:
        if low.startswith(konn):
            rest = s[len(konn):].lstrip(" :,–-")
            if len(rest) >= 3:
                s = rest
            break
    return s


def split_claims(answer: str) -> list[str]:
    """Zerlegt eine Antwort in prüfbare Aussagen.

    Zwei Schritte, bewusst regelbasiert und dependency-frei:
      1. an Satz- UND starken Klauselgrenzen (Semikolon) trennen → Atomisierung;
      2. je Fragment nicht-assertorische Rahmung/Konnektoren entfernen.

    Bleibt ein Proxy. TODO(mistral): echte atomare Claim-Extraktion modellbasiert —
    z. B. „X ist Y und Z" → [„X ist Y", „X ist Z"]. Konjunktionen (und/oder) werden
    hier NICHT gesplittet: in Nominalphrasen („Anmeldung und Signatur") entstünden
    subjektlose Fragmente, die die Deckung künstlich verschlechtern.
    """
    fragmente = re.split(r"(?<=[.!?])\s+|\n+|\s*;\s*", answer.strip())
    claims = []
    for frag in fragmente:
        frag = _strip_framing(frag)
        if len(frag) >= 3:
            claims.append(frag)
    return claims


def _band_for(min_cov: float) -> tuple[str, bool]:
    if min_cov >= GEDECKT_MIN:
        return "gedeckt", True
    if min_cov >= SCHWACH_MIN:
        return "schwach", False  # fail-closed: schwach wird nicht 1:1 ausgeliefert
    return "ungedeckt", False


def check(
    answer: str,
    sources: list[str],
    judge: Judge | None = None,
    question: str | None = None,
) -> GroundingResult:
    """Prüft eine Entwurfsantwort gegen abgerufene Quellabschnitte.

    `question` (optional) wird an den Judge weitergereicht: kurze Antwort-Fragmente
    sind nur relativ zur Frage prüfbar (siehe judge.py).
    """
    judge = judge or get_judge("heuristik")

    # Fail-closed: keine Quellen ⇒ nichts, wogegen man decken könnte.
    if not sources:
        return GroundingResult(
            band="ungedeckt", score=0.0, allow=False,
            reason="Keine Quellabschnitte abgerufen — Antwort kann nicht gedeckt sein.",
            judge=judge.name,
        )

    claims = split_claims(answer)
    if not claims:
        return GroundingResult(
            band="ungedeckt", score=0.0, allow=False,
            reason="Keine prüfbaren Aussagen in der Antwort.",
            judge=judge.name,
        )

    claim_results = []
    covs = []
    for claim in claims:
        cov = judge.coverage(claim, sources, question)
        covs.append(cov)
        claim_results.append({"text": claim, "coverage": round(cov, 3), "gedeckt": cov >= GEDECKT_MIN})

    min_cov = min(covs)
    band, allow = _band_for(min_cov)
    reasons = {
        "gedeckt": "Alle Aussagen ausreichend durch die Quellen gedeckt.",
        "schwach": "Mindestens eine Aussage nur teilweise gedeckt — nur belegten Teil ausliefern.",
        "ungedeckt": "Mindestens eine Aussage nicht durch die Quellen gedeckt — blockieren.",
    }
    return GroundingResult(
        band=band,
        score=round(min_cov, 3),
        allow=allow,
        claims=claim_results,
        reason=reasons[band],
        judge=judge.name,
    )
