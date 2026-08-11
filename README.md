# idaverbesserung — Grounding-Gate für „ida"

[![DOI](https://zenodo.org/badge/1330077281.svg)](https://doi.org/10.5281/zenodo.21888079)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Eine unabhängige Prüfschicht (**Grounding-Gate**), die jede Entwurfsantwort eines
RAG-Chatbots gegen die tatsächlich abgerufenen Quellabschnitte prüft, **bevor** sie
an Bürgerinnen und Bürger ausgeliefert wird. Im Zweifel: keine Antwort statt einer
falschen (fail-closed).

Motiviert durch den öffentlich gewordenen „Außenministerin"-Fehler des
österreichischen Verwaltungs-Chatbots **ida** (Start 08/2026): trotz RAG-Architektur
formulierte das Modell eine plausibel klingende, aber unbelegte Antwort.

## Prinzipien (nicht verhandelbar)

Das Gate darf die Architektur-Prinzipien von ida **nicht** brechen:

- **Nur europäisches LLM.** Der Prüfer ist selbst eine (zweite, unabhängige)
  Mistral-Instanz. Kein US-Modell im Antwortpfad.
- **On-Premise.** Läuft in derselben BRZ-LLMaaS-Umgebung wie der Generator.
  Keine externe API, keine US-Hyperscaler.
- **Unabhängiger Prüfer.** Getrennte Instanz statt Selbstbenotung.
- **Fail-closed by default.** Ungedeckt ⇒ blockieren.
- **Lückenloses Audit-Log.** Jede Ausgabe-/Block-Entscheidung mit Quellenbezug
  protokolliert (EU-AI-Act-anschlussfähig).

## Bänder

Analog zum Drift-Limiter, aber auf Deckung statt Ziel-Drift gemünzt:

| Band         | Bedeutung                                             | Aktion                          |
|--------------|-------------------------------------------------------|---------------------------------|
| `gedeckt`    | jede Aussage steht in den abgerufenen Quellen         | ausliefern                      |
| `schwach`    | teilweise gedeckt / unklar                            | nur belegten Teil, Rest offen   |
| `ungedeckt`  | keine oder widersprüchliche Deckung                   | **blockieren** + protokollieren |

## Status

**Lauffähiger Prototyp.** Wiederverwendet Muster aus dem Drift-Limiter-Projekt
(Audit-Log, Bänder, unabhängiger Prüfprozess). Die Kette ist end-to-end testbar:
`HeuristicJudge` läuft offline als transparenter Platzhalter, der `MistralJudge`-
Adapter ist implementiert (OpenAI-kompatible LLMaaS-API, Env-Config, stdlib-HTTP,
injizierbarer Transport, fail-closed). Offen bleibt die Kalibrierung gegen den
echten BRZ-Endpoint bzw. ein produktionsnahes starkes Mistral-Modell.

## Datenlage (Stand 10.08.2026)

- Die **4.600 Testfragen** aus ida's Testphase sind **nicht öffentlich**
  (internes Experten-Testing, kein Open-Data-Release).
- Die **FAQ-/Hilfe-Seiten** auf `oesterreich.gv.at` und `id-austria.gv.at`
  (inkl. Bereich „Hilfe zu ida") **sind** öffentlich und liefern strukturierte
  Frage→Antwort→Quelle-Tripel. Das ist unsere Ground-Truth-Wissensbasis.
  Quellenliste + Harvest-Plan: `harvest/README.md`.

## Layout

Siehe `PROJECT_STRUCTURE.md`.

## Lizenz

Apache License 2.0 — siehe `LICENSE`.
