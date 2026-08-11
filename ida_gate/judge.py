"""Der unabhängige Prüfer (Judge).

Kernidee (aus drift_limiter/checker.py übernommen): der Prüfer ist NICHT der
Generator. Er bekommt die Entwurfsantwort + die abgerufenen Quellabschnitte und
urteilt, ob die Antwort gedeckt ist.

Zwei Implementierungen:

1. `HeuristicJudge`  — transparenter Platzhalter, läuft offline, keine Deps.
   Nur Token-Überlappung. Reicht NICHT für Produktion, macht aber die ganze
   Kette (Harvest → Gate → Audit) sofort end-to-end testbar.

2. `MistralJudge`    — der eigentliche Prüfer: eine zweite, unabhängige
   Mistral-Instanz im BRZ (on-prem) bzw. ein OpenAI-kompatibler Proxy. Der
   Adapter ist implementiert; offen bleibt die Kalibrierung gegen den echten
   BRZ-Endpoint.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Callable, Protocol


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zäöüß0-9]+", text.lower()) if len(t) >= 3}


class Judge(Protocol):
    name: str

    def coverage(self, claim: str, sources: list[str], question: str | None = None) -> float:
        """0..1: wie gut ist `claim` durch die `sources` gedeckt?

        `question` ist optionaler Kontext: kurze Antwort-Fragmente („Nein, das ist
        nicht möglich.") sind nur RELATIV zur Frage prüfbar. Judges dürfen es nutzen.
        """
        ...


class HeuristicJudge:
    """Token-Überlappung als grober Deckungs-Proxy. NUR Platzhalter."""

    name = "heuristik"

    def coverage(self, claim: str, sources: list[str], question: str | None = None) -> float:
        claim_tokens = _tokens(claim)
        if not claim_tokens:
            return 0.0
        source_tokens: set[str] = set()
        for src in sources:
            source_tokens |= _tokens(src)
        if not source_tokens:
            return 0.0
        overlap = claim_tokens & source_tokens
        return len(overlap) / len(claim_tokens)


# Umgebungsvariablen — Endpoint/Key NIE hartkodieren (Randbedingung on-prem BRZ).
ENV_ENDPOINT = "IDA_MISTRAL_ENDPOINT"  # z. B. https://llmaas.brz.gv.at/v1/chat/completions
ENV_API_KEY = "IDA_MISTRAL_API_KEY"    # optional, je nach LLMaaS-Absicherung
ENV_MODEL = "IDA_MISTRAL_MODEL"        # exakte Variante ist öffentlich unbekannt

# Ein Transport bekommt die fertigen Chat-Messages und liefert den rohen
# Modell-Antworttext. Injizierbar → Tests laufen ohne Netz (siehe tests/).
Transport = Callable[[list[dict[str, str]]], str]


class MistralConfigError(RuntimeError):
    """Fehlkonfiguration (kein Endpoint/Transport) — soll laut scheitern, nicht blocken."""


ENTAILMENT_SYSTEM = (
    "Du bist ein strenger, unabhängiger Prüfer für eine Behörden-Auskunft. "
    "Entscheide ausschließlich anhand der QUELLEN, ob die AUSSAGE vollständig "
    "durch sie gedeckt ist. Nutze KEIN Vorwissen. Ist etwas nicht in den Quellen "
    "belegt, gilt es als nicht gedeckt. Antworte NUR mit einem JSON-Objekt der "
    'Form {"gedeckt": true|false, "beleg": "<wörtliches Zitat aus den Quellen '
    'oder null>"}. Kein weiterer Text.'
)


def _default_transport(
    endpoint: str,
    api_key: str | None,
    model: str,
    timeout: float,
) -> Transport:
    """Baut einen stdlib-HTTP-Transport gegen eine OpenAI-kompatible LLMaaS-API."""

    def call(messages: list[dict[str, str]]) -> str:
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": 0,      # deterministisch — ein Prüfer soll nicht würfeln
            "max_tokens": 300,
        }).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # OpenAI-kompatibles Schema; defensiv, falls Felder fehlen.
        return data["choices"][0]["message"]["content"]

    return call


class MistralJudge:
    """Zweite, unabhängige Mistral-Instanz als Entailment-Prüfer (on-prem BRZ).

    Kernidee: ein GETRENNTES Modell prüft Aussage-für-Aussage gegen die Quellen —
    nicht der Generator, der die Antwort formuliert hat. Deckt genau die Fälle ab,
    an denen der lexikalische HeuristicJudge scheitert (bedeutungsgleiche Synonyme).

    Konfiguration ausschließlich über Umgebungsvariablen (siehe ENV_*), damit
    Endpoint/Key nie im Code liegen. Für Tests kann ein `transport` injiziert
    werden — dann fällt jeder Netzaufruf weg (kein Netz im Default-Testpfad).

    Fail-closed: ist der Prüfer nicht erreichbar oder die Antwort unparsebar, gilt
    die Aussage als UNGEDECKT (coverage=0.0) → das Gate blockiert. Nur eine echte
    Fehlkonfiguration (weder Endpoint noch Transport) wirft laut `MistralConfigError`.
    """

    name = "mistral"

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        transport: Transport | None = None,
        timeout: float = 20.0,
    ) -> None:
        # Explizite Argumente haben Vorrang, sonst Umgebung, sonst Platzhalter.
        self.endpoint = endpoint or os.environ.get(ENV_ENDPOINT)
        self.api_key = api_key or os.environ.get(ENV_API_KEY)
        self.model = model or os.environ.get(ENV_MODEL) or "mistral-unbekannt"
        self.timeout = timeout
        self._transport = transport  # None → echter HTTP-Transport (lazy gebaut)

    def _build_messages(
        self, claim: str, sources: list[str], question: str | None = None
    ) -> list[dict[str, str]]:
        quellen = "\n\n".join(f"[Q{i+1}] {s}" for i, s in enumerate(sources))
        # Frage voranstellen, falls vorhanden: kurze Antwort-Fragmente sind sonst
        # kontextlos ("Nein, das ist nicht möglich.") und werden fälschlich als
        # ungedeckt gewertet — empirisch belegt gegen ein lokales Mistral.
        kopf = f"FRAGE:\n{question}\n\n" if question else ""
        user = f"{kopf}QUELLEN:\n{quellen}\n\nAUSSAGE:\n{claim}"
        return [
            {"role": "system", "content": ENTAILMENT_SYSTEM},
            {"role": "user", "content": user},
        ]

    def _transport_call(self, messages: list[dict[str, str]]) -> str:
        if self._transport is not None:
            return self._transport(messages)
        if not self.endpoint:
            raise MistralConfigError(
                f"{ENV_ENDPOINT} ist nicht gesetzt und kein Transport injiziert. "
                "BRZ-LLMaaS-Endpoint über Umgebungsvariablen konfigurieren."
            )
        self._transport = _default_transport(
            self.endpoint, self.api_key, self.model, self.timeout
        )
        return self._transport(messages)

    @staticmethod
    def _parse_score(raw: str) -> float:
        """Mappt die Modellantwort auf 0..1. Unparsebar ⇒ 0.0 (fail-closed)."""
        obj = _extract_json_object(raw)
        if obj is None:
            return 0.0
        # Optionaler feiner Score hat Vorrang, wenn valide.
        if "score" in obj:
            try:
                return max(0.0, min(1.0, float(obj["score"])))
            except (TypeError, ValueError):
                pass
        gedeckt = obj.get("gedeckt")
        if isinstance(gedeckt, bool):
            return 1.0 if gedeckt else 0.0
        if isinstance(gedeckt, str):
            return 1.0 if gedeckt.strip().lower() in {"true", "ja", "yes", "wahr"} else 0.0
        return 0.0

    def coverage(self, claim: str, sources: list[str], question: str | None = None) -> float:
        if not claim.strip() or not sources:
            return 0.0
        messages = self._build_messages(claim, sources, question)
        try:
            raw = self._transport_call(messages)
        except MistralConfigError:
            raise  # Fehlkonfiguration nicht verschlucken
        except Exception:
            return 0.0  # Prüfer unerreichbar/kaputt ⇒ fail-closed (blockieren)
        return self._parse_score(raw)


def _extract_json_object(text: str) -> dict | None:
    """Extrahiert das erste JSON-Objekt aus einem Modell-Text (robust ggü. Beiwerk)."""
    if not text:
        return None
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        return obj if isinstance(obj, dict) else None
                    except json.JSONDecodeError:
                        break  # ab nächster { erneut versuchen
        start = text.find("{", start + 1)
    return None


def get_judge(name: str = "heuristik") -> Judge:
    if name == "heuristik":
        return HeuristicJudge()
    if name == "mistral":
        return MistralJudge()
    raise ValueError(f"Unbekannter Judge: {name!r} (erlaubt: heuristik, mistral)")
