#!/usr/bin/env python3
"""Deterministischer Paraphrasierer für die Eval — Proxy für den Generator.

Warum? Der Eval-Harness kann positive Entwürfe entweder *wortgleich* aus der
Quelle spiegeln (trivialer Token-Overlap 1,0) oder — realistischer — so
umformulieren, wie ein echtes RAG-Modell antworten würde: dieselbe Aussage,
andere Wörter. Genau das trennt einen treuen Paraphrase-Entwurf von einer
Halluzination NICHT mehr auf Wortebene — und legt die blinde Stelle des
lexikalischen `HeuristicJudge` offen.

Bewusst regelbasiert, dependency-frei und deterministisch:
  1. Kondensieren  — nur die ersten ein bis zwei Sätze (Modelle fassen zusammen).
  2. Synonyme      — bedeutungserhaltende Wort-Swaps aus dem ID-Austria-Vokabular.
  3. Rahmung       — eine neutrale einleitende Wendung, wie sie Generatoren setzen.

KEIN Anspruch auf linguistische Perfektion. Der Zweck ist, den Wort-Overlap
messbar UND bedeutungserhaltend zu senken — nicht, einen echten Generator zu
ersetzen. Sobald der BRZ-Mistral-Endpoint steht, ist das hier obsolet.
"""

from __future__ import annotations

import re

# Bedeutungserhaltende Synonyme: Quellwort → Paraphrase. Konservativ gehalten —
# jedes Paar muss inhaltlich unstrittig gleich sein. Groß-/Kleinschreibung des
# ersten Buchstabens wird beim Ersetzen übernommen.
SYNONYME: dict[str, str] = {
    "anmelden": "einloggen",
    "anmeldung": "login",
    "anmeldungen": "logins",
    "app": "anwendung",
    "ermöglicht": "erlaubt",
    "ermöglichen": "erlauben",
    "benutzt": "verwendet",
    "benutzen": "nutzen",
    "verwenden": "nutzen",
    "verwendet": "genutzt",
    "smartphone": "handy",
    "gesichtserkennung": "gesichtsscan",
    "fingerprint": "fingerabdruck",
    "bestätigen": "verifizieren",
    "durchführen": "vornehmen",
    "durchzuführen": "vorzunehmen",
    "erhalten": "bekommen",
    "geeignet": "passend",
    "vermutlich": "wahrscheinlich",
    "erklärung": "grund",
    "alternative": "option",
    "webbrowser": "browser",
    "notwendig": "erforderlich",
    "möglichkeit": "option",
    "zusenden": "schicken",
    "benachrichtigung": "hinweis",
    "person": "jemand",
    "sicherheitsschlüssel": "security-key",
}

# Neutrale Einleitungen — so, wie ein Assistent eine Antwort rahmt. Deterministisch
# nach Länge des Quelltexts gewählt (kein Zufall → reproduzierbare Eval).
RAHMEN = ["Kurz gesagt:", "Grundsätzlich gilt:", "Im Wesentlichen:"]

_WORT = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def _ersetze_wort(match: re.Match[str]) -> str:
    wort = match.group(0)
    ersatz = SYNONYME.get(wort.lower())
    if ersatz is None:
        return wort
    # Erste-Buchstabe-Großschreibung des Originals übernehmen.
    return ersatz[0].upper() + ersatz[1:] if wort[:1].isupper() else ersatz


def _erste_saetze(text: str, n: int = 2) -> str:
    saetze = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(saetze[:n]).strip()


def paraphrasiere(antwort: str) -> str:
    """Formt eine FAQ-Antwort zu einem plausiblen, bedeutungsgleichen Entwurf um."""
    kern = _erste_saetze(antwort, n=2)
    umformuliert = _WORT.sub(_ersetze_wort, kern)
    rahmen = RAHMEN[len(antwort) % len(RAHMEN)]
    return f"{rahmen} {umformuliert}".strip()


if __name__ == "__main__":  # kleine Sichtprüfung
    beispiel = (
        "Die angemeldete App „ID Austria“ ermöglicht es, sich bei Online-Services "
        "mittels Biometrie anzumelden. Dafür benutzt die App ein Gerätepasswort."
    )
    print("Original:    ", beispiel)
    print("Paraphrase:  ", paraphrasiere(beispiel))
