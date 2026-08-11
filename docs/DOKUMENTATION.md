# Dokumentation — idaverbesserung / ida_gate

Technische Referenz des Grounding-Gates. Für den Überblick siehe `README.md`,
für die Projektstruktur `PROJECT_STRUCTURE.md`.

---

## 1. Idee

Ein RAG-Chatbot (wie ida) ruft Quellabschnitte ab und lässt ein Sprachmodell
daraus eine Antwort formulieren. Fehlt eine Prüfung, ob die Antwort auch wirklich
durch die Abschnitte **gedeckt** ist, kann das Modell plausibel klingenden, aber
unbelegten Text erzeugen (Halluzination).

Das **Grounding-Gate** schaltet sich zwischen Entwurf und Ausgabe:

```
Frage → [Retrieval] → Abschnitte → [Generator: Mistral] → Entwurfsantwort
                                                              │
                                          ┌───────────────────┘
                                          ▼
              [Grounding-Gate: 2. Mistral, unabhängig]
              prüft Aussage für Aussage gegen die Abschnitte
                                          │
                 gedeckt ─► ausliefern    │    ungedeckt ─► blockieren + Log
```

## 2. Bänder

| Band        | Bedingung (Deckungsgrad der schwächsten Aussage) | `allow` |
|-------------|--------------------------------------------------|:-------:|
| `gedeckt`   | ≥ `GEDECKT_MIN` (0.75)                            | True    |
| `schwach`   | ≥ `SCHWACH_MIN` (0.40)                            | False   |
| `ungedeckt` | darunter, oder keine Quellen / keine Aussagen     | False   |

Fail-closed: `schwach` wird bewusst nicht 1:1 ausgeliefert. Schwellen in
`ida_gate/gate.py`.

## 3. Modul-Referenz (`ida_gate/`)

| Modul        | Inhalt |
|--------------|--------|
| `models.py`  | Datenklassen `FAQItem` (mit `ist_frage`), `TestQuestion`, `GroundingResult`, `AuditEvent`. |
| `store.py`   | Append-only Audit-Log unter `.ida-gate/events.jsonl` (aus `drift_limiter/store.py` adaptiert). |
| `judge.py`   | Prüfer: `HeuristicJudge` (Token-Überlappung, läuft offline) + implementierter `MistralJudge`-Adapter für OpenAI-kompatible LLMaaS-Endpoints. `get_judge(name)`. |
| `gate.py`    | `split_claims()`, `check(answer, sources, judge, question=None)` → `GroundingResult`. Band-Logik. |
| `cli.py`     | Befehle `check`, `harvest`, `build-testset`. |

### `gate.check(answer, sources, judge=None, question=None) -> GroundingResult`

- Zerlegt `answer` in Aussagen (`split_claims`, satzbasiert — Platzhalter).
- Lässt jede Aussage vom `judge` bewerten (0..1 Deckungsgrad).
- Aggregiert über die **schwächste** Aussage zum Band.
- Fail-closed: keine `sources` oder keine Aussagen ⇒ `ungedeckt`.
- Reicht die optionale Nutzerfrage an den Judge weiter; das hilft bei kurzen
  Antwortfragmenten wie „Nein, das ist nicht möglich.", die ohne Fragekontext
  nicht sauber prüfbar sind.

### Prüfer-Interface (`judge.Judge`)

```python
class Judge(Protocol):
    name: str
    def coverage(self, claim: str, sources: list[str], question: str | None = None) -> float: ...
```

`MistralJudge`: zweite, unabhängige Mistral-Instanz im BRZ oder ein
OpenAI-kompatibler Proxy. Prompt fragt „Ist die AUSSAGE ausschließlich durch die
QUELLEN gedeckt?", Antwort JSON, Mapping auf 0..1. Endpoint/Key kommen aus
Umgebungsvariablen, nie hartkodiert. Der Transport ist injizierbar; deshalb laufen
die Tests ohne Netz. Ist der Prüfer nicht erreichbar oder antwortet unparsebar,
gilt die Aussage als ungedeckt (fail-closed). Eine echte Fehlkonfiguration wirft
`MistralConfigError`.

## 4. Daten

### 4.1 Wissensbasis — `data/faq/ida_faq.jsonl` (+ `.csv`)

Ein `FAQItem` je Zeile:

```json
{"frage": "...", "antwort": "...", "quelle_url": "https://www.id-austria.gv.at/...",
 "kategorie": "hilfe-zu-ida", "stand": "2026-02-25", "ist_frage": true}
```

- `stand` = `lastmod` aus `sitemap.xml` (Aktualitäts-Signal).
- `ist_frage` = echte Nutzerfrage (True) vs. Abschnitts-Überschrift (False).
- Rohfassung (ungefiltert) in `ida_faq.raw.jsonl`.
- Bestand: 158 Tripel (126 Fragen + 32 Abschnitte) aus 44/45 ida-Kern-Seiten.

### 4.2 Testset — `data/testsets/testset.jsonl`

Ein `TestQuestion` je Zeile:

```json
{"frage": "...", "erwartet": "gedeckt|ungedeckt", "notiz": "..."}
```

- `erwartet="gedeckt"`: aus der Wissensbasis → Gate soll durchlassen (mit passender Quelle).
- `erwartet="ungedeckt"`: Falle außerhalb der Wissensbasis → Gate muss blocken.
- Bestand: 40 (32 gedeckt + 8 Fallen, inkl. „Wer ist Außenministerin?").

## 5. Pipeline (`harvest/`)

| Skript             | Funktion |
|--------------------|----------|
| `harvest.py`       | `sitemap.xml` → ida-Kern-URLs filtern → fetchen → parsen → `clean_items` → schreiben. |
| `clean.py`         | Normalisierung (N1–N5) + Entfernen (D1/D2) + `ist_frage`-Klassifikation. Idempotent. |
| `build_testset.py` | positive Fälle aus `ist_frage=True` (dedupliziert) + kuratierte Negativ-Fallen. |

### Bereinigungsregeln (Details)

- **N1** gespreizte Bindestriche aus leeren Inline-Tags: `SMS - TAN` → `SMS-TAN`.
- **N2** Leerzeichen vor Satzzeichen: `App ?` → `App?`.
- **N3** Leerzeichen in `„ …"`: `„ ID` → `„ID`.
- **N4** Domain-Tippfehler: `osterreich.gv.at` → `oesterreich.gv.at`.
- **N5** Mehrfach-Leerzeichen → eines, trimmen.
- **D1** reine Kontakt-CTA entfernt, **D2** exakte Duplikate entfernt.

Legitime Gedankenstriche (`–`) und Zahlen bleiben unangetastet (getestet).

### Quelle & Etikette

- Host: `www.id-austria.gv.at`, Bereiche `hilfe-zu-ida`, `hilfe-zur-app-ida`.
- robots.txt erlaubt `/de/hilfe/*`. Drosselung ~0,5 Req/s, eigener User-Agent.
- Roh-HTML wird in `data/raw/` gesichert (Reproduzierbarkeit).

## 6. CLI

```bash
python3 -m ida_gate.cli check \
  --question "<Nutzerfrage>" \
  --answer   "<Entwurfsantwort>" \
  --source   "<abgerufener Abschnitt>" [--source ...] \
  --judge heuristik|mistral \
  --fail-on-block          # Exit-Code 2 bei Block
```

Ausgabe: `GroundingResult` als JSON. Jede Prüfung landet im Audit-Log
`.ida-gate/events.jsonl` (Feld `--workspace` steuert das Verzeichnis).

## 7. Grenzen

- Der `HeuristicJudge` ist ein grober Proxy — echte Deckungsprüfung erst mit
  `MistralJudge`.
- Ein Gate heilt keinen veralteten Index; `stand` macht Alter sichtbar, ersetzt
  aber keine Index-Aktualisierung.
- Zusatzkosten: ein zweiter Mistral-Aufruf pro Antwort (Latenz/Compute).
- Kein 100%-Schutz — reduziert Halluzinationen sichtbar und auditierbar.
