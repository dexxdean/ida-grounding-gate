"""CLI für ida_gate.

Verfügbar:
  check          eine Entwurfsantwort gegen Quellabschnitte prüfen
  harvest        FAQ-Seiten in data/faq/ einsammeln
  build-testset  Testfragen inkl. Negativ-Fallen erzeugen
"""

from __future__ import annotations

import argparse
import importlib
import json

from .gate import check
from .judge import get_judge
from .models import AuditEvent
from .store import append_event


def _cmd_check(args: argparse.Namespace) -> int:
    sources = list(args.source or [])
    judge = get_judge(args.judge)
    result = check(args.answer, sources, judge=judge, question=args.question or None)

    append_event(
        args.workspace,
        AuditEvent(
            kind="gate_check",
            frage=args.question or "",
            band=result.band,
            allow=result.allow,
            judge=result.judge,
            sources=sources,
            detail=result.to_dict(),
        ),
    )

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    if not result.allow and args.fail_on_block:
        return 2
    return 0


def _run_module_main(module_name: str) -> int:
    module = importlib.import_module(module_name)
    return int(module.main())


def _cmd_harvest(args: argparse.Namespace) -> int:
    return _run_module_main("harvest.harvest")


def _cmd_build_testset(args: argparse.Namespace) -> int:
    return _run_module_main("harvest.build_testset")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ida-gate", description="Grounding-Gate für RAG-Antworten.")
    p.add_argument("--workspace", default=".", help="Verzeichnis für .ida-gate/ (Audit-Log).")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="Entwurfsantwort gegen Quellabschnitte prüfen.")
    c.add_argument("--answer", required=True, help="Die Entwurfsantwort des Generators.")
    c.add_argument("--source", action="append", help="Ein abgerufener Quellabschnitt (mehrfach).")
    c.add_argument("--question", default="", help="Die ursprüngliche Nutzerfrage (für's Log).")
    c.add_argument("--judge", default="heuristik", choices=["heuristik", "mistral"])
    c.add_argument("--fail-on-block", action="store_true", help="Exit-Code 2 bei Block.")
    c.set_defaults(func=_cmd_check)

    h = sub.add_parser("harvest", help="FAQ-Seiten einsammeln.")
    h.set_defaults(func=_cmd_harvest)

    bt = sub.add_parser("build-testset", help="Testfragen inkl. Fallen erzeugen.")
    bt.set_defaults(func=_cmd_build_testset)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
