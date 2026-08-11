# idaverbesserung — Grounding-Gate für „ida"

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

**Frühes Gerüst.** Wiederverwendet Muster aus dem Drift-Limiter-Projekt
(Audit-Log, Bänder, unabhängiger Prüfprozess). Der eigentliche Deckungs-Check
(Aussage ⟷ Absatz) via Mistral ist **noch nicht** implementiert — siehe
`ida_gate/judge.py` (`TODO: Mistral-Adapter`). Aktuell läuft ein transparenter
Heuristik-Prüfer als Platzhalter, damit die Kette end-to-end testbar ist.

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
