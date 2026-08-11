# Projektstruktur

```
idaverbesserung/
├── README.md                 Projektüberblick, Prinzipien, Status
├── PROJECT_STRUCTURE.md      diese Datei
├── pyproject.toml            Paketdefinition (Python ≥ 3.10, keine Zwangs-Deps)
│
├── ida_gate/                 das Python-Paket (die Prüfschicht)
│   ├── __init__.py
│   ├── models.py             Datenklassen: FAQItem, TestQuestion,
│   │                         GroundingResult, AuditEvent
│   ├── store.py              Audit-Log (.ida-gate/events.jsonl) —
│   │                         Muster aus drift_limiter/store.py adaptiert
│   ├── gate.py               Kern: Band-Logik gedeckt/schwach/ungedeckt
│   ├── judge.py              Prüfer-Interface: Heuristik-Fallback (läuft offline)
│   │                         + Mistral-Adapter (TODO, on-prem)
│   └── cli.py                CLI: harvest · build-testset · check
│
├── data/
│   ├── raw/                  46 gesicherte Roh-HTML-Seiten
│   ├── faq/                  ida_faq.jsonl/.csv (158 Tripel, Feld ist_frage)
│   │                         + ida_faq.raw.jsonl (Rohfassung, 170 Blöcke)
│   └── testsets/            testset.jsonl (32 gedeckt / 8 Fallen)
│
├── harvest/                  Daten-Beschaffung (stdlib, dependency-frei)
│   ├── README.md             Quell-URLs, Pipeline, Bereinigungsregeln
│   ├── harvest.py            Sitemap → Fetch → Parse → clean → data/faq/
│   ├── clean.py              Normalisierung + Klassifikation (ist_frage)
│   └── build_testset.py      positive Fragen + Negativ-Fallen → data/testsets/
│
├── eval/                     Evaluierung: Recall auf Fallen, Übervorsicht, Latenz
│   ├── README.md             Kennzahlen, Modi, Baseline-Tabelle
│   ├── run_eval.py           Harness: Retrieval+Entwurf → gate.check → Kennzahlen
│   └── paraphrase.py         deterministischer Paraphrasierer (Generator-Proxy)
│
├── tests/                    dependency-freie Tests (pytest ODER pur python3)
│   └── test_mistral_judge.py Env-Config, Score-Mapping, fail-closed (injiz. Transport)
│
└── docs/
    ├── grounding-gate-ida.html   Konzeptpapier (One-Pager) für BRZ/BKA
    └── ida-fakten.md             belegte ida-Fakten (Technik + Vorfall, mit Quellen)
```

## Was aus dem Drift-Limiter übernommen wurde

| Baustein            | Herkunft                        | Anpassung für ida                          |
|---------------------|---------------------------------|--------------------------------------------|
| Audit-Log           | `drift_limiter/store.py`        | `.ida-gate/events.jsonl`, Grounding-Events |
| Bänder + Severity   | `drift_limiter` scoring/checker | on_target/watch/stop → gedeckt/schwach/ungedeckt |
| Unabhängiger Prüfer | `drift_limiter/checker.py`      | Selbstbenotung ⇒ getrennte Mistral-Instanz |
| Grounding-Disziplin | `document-audit`-Policy         | „ohne Deckung nicht antworten"             |

**Nicht** übernommen: die Task-Drift-Logik selbst (Ziel-Abdriften über lange
Workflows) — sie löst ida's Einzel-Turn-Halluzination nicht.
