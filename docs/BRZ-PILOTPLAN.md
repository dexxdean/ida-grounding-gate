# BRZ-Pilotplan — ida Grounding-Gate

Stand: 2026-08-10  
Ziel: Zweiwöchiger Shadow-Pilot zur produktionsnahen Kalibrierung des Grounding-Gates

## Ziel

Das Gate läuft im Shadow Mode neben der bestehenden ida-Pipeline. Es blockiert
noch keine Bürgerantworten, protokolliert aber für jede Entwurfsantwort, ob sie
aus Sicht des Gates auslieferbar, reparierbar, zu blockieren oder zu eskalieren
wäre.

## Woche 1 — Anschluss und Baseline

1. Technischer Zugang
   - abgesicherter BRZ-LLMaaS-Test-Endpoint
   - Modellname/Deployment-ID als Konfiguration, nicht im Code
   - Testumgebung ohne personenbezogene Produktivdaten

2. Datenbasis
   - bestehendes 40-Fall-Testset laufen lassen
   - internes 4.600-Fragen-Set, falls verfügbar, als Replay verwenden
   - zusätzlich 50-100 Negativ-Fallen kuratieren

3. Shadow-Run
   - CalibrateState klassifiziert jede Anfrage vor Retrieval/Generation im
     Hintergrund
   - ida-Retrieval liefert SourcePacket
   - Generator liefert DraftAnswer
   - Gate liefert GroundingResult + DriftReport
   - keine echte Bürgerantwort wird durch den Prototyp verändert

## Woche 2 — Kalibrierung und Abnahme

1. Schwellen kalibrieren
   - `GEDECKT_MIN`
   - `SCHWACH_MIN`
   - Frage-Kontext AN/AUS
   - Umgang mit kurzen Antwortfragmenten

2. Fehleranalyse
   - falsch geblockte gedeckte Antworten
   - durchgelassene Fallen, falls vorhanden
   - unparsebare Judge-Antworten
   - Latenz-Ausreißer
   - Fälle mit widersprüchlichen Quellen

3. Regression
   - bestätigte Fehler als NegativeEvidence erfassen
   - daraus Regressionstests erzeugen
   - erneuten Eval-Lauf speichern

4. Go/No-Go-Kriterien
   - Fallen-Recall auf vereinbartem Negativset
   - maximale Übervorsicht auf gedeckten FAQ-Fragen
   - Latenz p50/p95
   - Fail-closed-Verhalten bei Endpoint-Fehlern
   - Fachstellen-Akzeptanz der Block-/Repair-Texte

## Metriken

| Metrik | Bedeutung |
|---|---|
| Fallen-Recall | Anteil der Out-of-scope-/Halluzinationsfallen, die nicht ausgeliefert werden |
| Übervorsicht | Anteil korrekter, gedeckter Antworten, die fälschlich blockiert werden |
| Repair-Rate | Anteil schwacher Entwürfe, die auf belegten Teil reduziert werden können |
| Latenz p50/p95 | zusätzlicher Zeitbedarf des Gates |
| Unparseable-Rate | Anteil unbrauchbarer Judge-Antworten |
| Fail-closed-Rate | Anteil Blockaden durch fehlende Quellen, Endpoint-Fehler oder unparsebare Antworten |
| Freshness-Flags | Anteil Antworten mit veralteten oder unklar datierten Quellen |

## Lieferobjekte nach dem Pilot

- Eval-Report mit Run-ID, Modell, Prompt-Version und Datenhash
- Liste aller blockierten/reparierten Fälle
- Liste der Fälle, in denen CalibrateState eine sichtbare Rückfrage empfohlen hätte
- NegativeEvidence-Log mit Korrektur und Follow-up-Test
- Schwellenempfehlung für BRZ-Modell
- Entscheidung: weiter Shadow Mode, begrenzter Produktivtest oder Rückbau

## Claim-Grenze

Der Pilot beweist keine vollständige Fehlerfreiheit. Er prüft, ob eine
ausgabeseitige Deckungs- und Driftkontrolle den bekannten Fehlertyp praktisch
reduziert, sichtbar macht und in Regressionstests überführt.
