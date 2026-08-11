# Evaluierung

Misst, was das Grounding-Gate auf dem Testset leistet. Dependency-frei, offline.

```bash
python3 eval/run_eval.py                    # Vergleich spiegel vs. paraphrase (Default)
python3 eval/run_eval.py --mode paraphrase  # nur der realistische Modus
python3 eval/run_eval.py --mode spiegel     # nur Verdrahtungs-Check (Overlap trivial)
python3 eval/run_eval.py --json             # maschinenlesbar (Zeilen + Kennzahlen)
python3 eval/run_eval.py --judge mistral    # mit konfiguriertem LLMaaS-/Ollama-Endpoint
```

## Kennzahlen

- **Fallen-Recall** — Anteil der 8 Negativ-Fallen, die korrekt geblockt werden.
  Das Kernversprechen: kein Raten außerhalb der Wissensbasis.
- **Übervorsicht** — Anteil der gedeckten Fragen, die fälschlich geblockt werden
  (die Kosten des Gates für echte Nutzer).
- **Genauigkeit** / **Latenz p50, max**.

## Wie der Harness Retrieval + Entwurf nachbildet

Das Gate prüft `answer` gegen `sources`. Für eine reproduzierbare Baseline ohne
Netz/LLM bilden wir beides nach (`run_eval.py`):

- **Retrieval**: Token-Overlap-Suche über die Wissensbasis → Top-k Antworten.
- **Entwurf** der gedeckten Fragen, zwei Modi:
  - `spiegel` — Entwurf = Quelltext 1:1. Nur Verdrahtungs-Check; Overlap trivial 1,0.
  - `paraphrase` — Entwurf umformuliert wie ein echter Generator
    (`paraphrase.py`: Kondensation + bedeutungserhaltende Synonyme + Rahmung).
- **Entwurf** der Fallen: plausible Halluzination aus Parameterwissen
  (z. B. „Die Außenministerin ist …") — vom Retrieval nicht gedeckt.

## Baseline (Stand 2026-08-10, HeuristicJudge, top-k=3)

| Kennzahl        | spiegel | paraphrase (vor Claim-Extr.) | paraphrase (nach Claim-Extr.) |
|-----------------|--------:|-----------------------------:|------------------------------:|
| Fallen-Recall   |   100 % |                        100 % |                         100 % |
| Übervorsicht    |     0 % |                       18,8 % |                         3,1 % |
| Genauigkeit     |   100 % |                         85 % |                        97,5 % |

**Der Befund liegt im Kontrast.** Der `spiegel`-Wert (0 % Übervorsicht) zeigt nur,
dass die Kette sauber verdrahtet ist. Sobald der Entwurf *bedeutungsgleich
umformuliert* ist, blockt der lexikalische `HeuristicJudge` zunächst 6 von 32
korrekten Antworten fälschlich (Scores 0,69–0,73, knapp unter `GEDECKT_MIN=0.75`).

**Verbesserte Claim-Extraktion** (`gate.split_claims`) entfernt vor der Prüfung
nicht-assertorische Diskurs-Rahmung („Kurz gesagt", „Grundsätzlich gilt", …) —
empirisch die dominante Miss-Ursache. Das senkt die Übervorsicht auf **3,1 %**
(nur noch 1 Fehlblock), ohne einen Fallen-Recall-Verlust. Der **verbleibende**
Fehlblock ist rein **semantisch** (Synonyme: „App"→„Anwendung",
„ermöglicht"→„erlaubt", „Fingerprint"→„Fingerabdruck") — lexikalisch nicht
auflösbar. Genau dafür ist der `MistralJudge` gedacht: Entailment statt
Wort-Overlap.

## Proxy-Befund mit MistralJudge

Der `MistralJudge` ist als Adapter implementiert und wurde lokal gegen
OpenAI-kompatible Ollama-Endpoints getestet. Der relevante Proxy-Lauf ist NeMo 12B:

| Judge / Modus | Fallen-Recall | Übervorsicht | Genauigkeit |
|---|---:|---:|---:|
| NeMo 12B, mit Frage-Kontext | 100 % | 3,1 % | 97,5 % |
| NeMo 12B, ohne Frage-Kontext | 100 % | 9,4 % | 92,5 % |

Interpretation: Für die aktuelle Proxy-Konfiguration bleibt Frage-Kontext
standardmäßig AN. Die produktionsnahe Präzision muss trotzdem am echten
BRZ-Endpoint bzw. einem stärkeren produktionsnahen Modell kalibriert werden.
