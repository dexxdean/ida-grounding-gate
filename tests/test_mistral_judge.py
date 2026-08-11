#!/usr/bin/env python3
"""Tests für den MistralJudge — ohne Netz, über injizierten Transport.

Prüft die Logik rund um den LLM-Aufruf (Prompt-Bau, Score-Mapping, fail-closed),
NICHT den echten BRZ-Endpoint. Läuft unter pytest oder direkt:

    python3 tests/test_mistral_judge.py     # eigener Runner, kein pytest nötig
    pytest tests/test_mistral_judge.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ida_gate import gate
from ida_gate.judge import (
    ENV_ENDPOINT,
    MistralConfigError,
    MistralJudge,
    _extract_json_object,
    get_judge,
)

SOURCES = ["Die ID Austria ist kostenlos und in ganz Österreich gültig."]


def _stub(response: str):
    """Transport, der eine feste Antwort liefert und die Messages mitschneidet."""
    aufgezeichnet: list[list[dict[str, str]]] = []

    def transport(messages: list[dict[str, str]]) -> str:
        aufgezeichnet.append(messages)
        return response

    transport.calls = aufgezeichnet  # type: ignore[attr-defined]
    return transport


def test_gedeckt_true_gibt_1() -> None:
    j = MistralJudge(transport=_stub('{"gedeckt": true, "beleg": "ID Austria ist kostenlos"}'))
    assert j.coverage("Die ID Austria ist kostenlos.", SOURCES) == 1.0


def test_gedeckt_false_gibt_0() -> None:
    j = MistralJudge(transport=_stub('{"gedeckt": false, "beleg": null}'))
    assert j.coverage("Die ID Austria kostet 30 Euro.", SOURCES) == 0.0


def test_optionaler_score_wird_geklemmt() -> None:
    assert MistralJudge(transport=_stub('{"score": 0.4}')).coverage("x y z", SOURCES) == 0.4
    assert MistralJudge(transport=_stub('{"score": 5}')).coverage("x y z", SOURCES) == 1.0
    assert MistralJudge(transport=_stub('{"score": -2}')).coverage("x y z", SOURCES) == 0.0


def test_json_mit_beiwerk_wird_extrahiert() -> None:
    raw = 'Hier mein Urteil:\n```json\n{"gedeckt": true}\n```\nDanke!'
    assert MistralJudge(transport=_stub(raw)).coverage("a b c", SOURCES) == 1.0


def test_unparsebar_ist_fail_closed() -> None:
    assert MistralJudge(transport=_stub("völliger Unsinn ohne JSON")).coverage("a b c", SOURCES) == 0.0


def test_transportfehler_ist_fail_closed() -> None:
    def kaputt(_messages):
        raise TimeoutError("Endpoint nicht erreichbar")

    assert MistralJudge(transport=kaputt).coverage("a b c", SOURCES) == 0.0


def test_leere_eingaben_geben_0() -> None:
    j = MistralJudge(transport=_stub('{"gedeckt": true}'))
    assert j.coverage("", SOURCES) == 0.0
    assert j.coverage("Aussage", []) == 0.0


def test_fehlkonfiguration_wirft(monkeypatch=None) -> None:
    # Weder Endpoint noch Transport → laut scheitern, NICHT still blocken.
    import os
    alt = os.environ.pop(ENV_ENDPOINT, None)
    try:
        j = MistralJudge()  # kein Transport, kein Env-Endpoint
        raised = False
        try:
            j.coverage("a b c", SOURCES)
        except MistralConfigError:
            raised = True
        assert raised, "MistralConfigError erwartet, wenn nichts konfiguriert ist"
    finally:
        if alt is not None:
            os.environ[ENV_ENDPOINT] = alt


def test_prompt_enthaelt_quellen_und_aussage() -> None:
    stub = _stub('{"gedeckt": true}')
    MistralJudge(transport=stub).coverage("Die ID Austria ist kostenlos.", SOURCES)
    system, user = stub.calls[0]  # type: ignore[attr-defined]
    assert system["role"] == "system" and "gedeckt" in system["content"]
    assert "QUELLEN:" in user["content"] and "AUSSAGE:" in user["content"]
    assert "kostenlos" in user["content"]  # Quelle eingebettet
    assert "FRAGE:" not in user["content"]  # ohne question kein Frage-Kopf


def test_frage_kontext_wird_eingebettet() -> None:
    stub = _stub('{"gedeckt": true}')
    MistralJudge(transport=stub).coverage(
        "Nein, das ist nicht möglich.", SOURCES, question="Kann ich das Passwort wählen?"
    )
    _system, user = stub.calls[0]  # type: ignore[attr-defined]
    assert "FRAGE:" in user["content"] and "Passwort wählen" in user["content"]


def test_env_konfiguration(monkeypatch=None) -> None:
    import os
    os.environ[ENV_ENDPOINT] = "https://llmaas.example.brz.gv.at/v1/chat/completions"
    try:
        j = MistralJudge()
        assert j.endpoint.endswith("/chat/completions")
    finally:
        os.environ.pop(ENV_ENDPOINT, None)


def test_gate_integration_mit_stub() -> None:
    # Der MistralJudge lässt sich 1:1 ins Gate einhängen (Judge-Protokoll).
    judge = MistralJudge(transport=_stub('{"gedeckt": true}'))
    res = gate.check("Die ID Austria ist kostenlos.", SOURCES, judge=judge)
    assert res.judge == "mistral" and res.allow is True and res.band == "gedeckt"

    judge_block = MistralJudge(transport=_stub('{"gedeckt": false}'))
    res2 = gate.check("Die ID Austria kostet 30 Euro.", SOURCES, judge=judge_block)
    assert res2.allow is False and res2.band == "ungedeckt"


def test_extract_json_helper() -> None:
    assert _extract_json_object('{"a": 1}') == {"a": 1}
    assert _extract_json_object("kein json") is None
    assert _extract_json_object('[1,2,3]') is None  # Array ist kein Objekt
    assert _extract_json_object('Text {"x": {"y": 2}} Rest') == {"x": {"y": 2}}


def _run_standalone() -> int:
    """Minimaler Runner, damit die Tests ohne pytest laufen."""
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    fehler = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as e:
            fehler += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            fehler += 1
            print(f"  ERR  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - fehler}/{len(tests)} bestanden.")
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(_run_standalone())
