# BRZ-Technik-Abgleich für ida_gate

Stand: 2026-08-10  
Quelle: https://www.brz.gv.at/presse/technischer-hintergrund-ida.html

## Warum dieser Abgleich wichtig ist

Die BRZ-Beschreibung zeigt ida nicht als frei laufenden Chatbot, sondern als
RAG-System mit Sicherheitsmechanismen für Ein- und Ausgaben, den Wissensbasen
`oesterreich.gv.at` und `id-austria.gv.at`, BRZ-LLMaaS, europäischem Mistral-Modell
und Betrieb in Österreich/on-prem.

Das ändert die Bewertung von Dejans Prototyp: Das Gate ist nicht als Ersatz für
die ida-Architektur zu verstehen, sondern als ergänzender Kontrollbaustein in
dieser bestehenden Pipeline.

## Passender Einbaupunkt

Empfohlene Zielarchitektur:

```text
Nutzerfrage
  -> Ida Frontend
  -> Input-Sicherheitsmechanismen + CalibrateState
  -> RAG / Source Selection
  -> Generator über BRZ-LLMaaS
  -> Output-Sicherheitsmechanismen + Grounding-Gate
  -> OutputContract / Quellenanzeige / Antwort
```

Dejans aktueller Prototyp sitzt vor allem rechts in dieser Kette:

```text
DraftAnswer + Quellen -> Grounding-Gate -> allow/block
```

Das ist sinnvoll, aber noch nicht vollständig. Der neue technische Hintergrund
legt nahe, dass zwei Schichten unterschieden werden müssen:

1. Eingangsseite: CalibrateState klassifiziert Frage, Risiko, Scope und
   Quellenpolitik, bevor RAG und Generator arbeiten.
2. Ausgangsseite: Grounding-Gate prüft die Entwurfsantwort gegen die tatsächlich
   abgerufenen Quellen.

## CalibrateState: Hintergrund zuerst, Nachfrage nur wenn nötig

CalibrateState sollte für Nutzerinnen und Nutzer normalerweise unsichtbar laufen.
Er ist ein Router und Sicherheitsmechanismus, kein zusätzliches Formular.

Intern sollte er entscheiden:

- Ist die Frage im ida-Mandat?
- Betrifft sie ID Austria, eAusweise, digitale Signatur, Wohnsitz oder allgemeine
  Verwaltung?
- Reicht FAQ-Wissen oder braucht es eine aktuelle autoritative Quelle?
- Handelt es sich um Frist, Gebühr, Zuständigkeit, rechtlich heikle Aussage,
  personenbezogene Auskunft oder Hot Fact?
- Darf direkt geantwortet werden, soll repariert, blockiert oder eskaliert werden?

Sichtbar wird CalibrateState nur als kurze Rückfrage, wenn die Klärung den
Antwortpfad tatsächlich ändert und keine unnötigen personenbezogenen Daten
erfragt. Gute Rückfragen sind zum Beispiel:

- „Meinen Sie die Registrierung der ID Austria oder die Verknüpfung in der App?“
- „Geht es um eine allgemeine Information oder um ein konkretes Login-Problem?“
- „Betrifft die Frage einen bestimmten Antragstyp?“

Schlechte Rückfragen sind solche, die nur Unsicherheit kaschieren oder Daten
einsammeln, die für eine öffentliche Erstinformation nicht nötig sind.

## Was Dejans Prototyp vor diesem Hintergrund gut trifft

- RAG-kompatible Position: Er prüft Entwurfsantworten gegen abgerufene Quellen.
- BRZ-kompatible Konfiguration: Der `MistralJudge` nutzt einen konfigurierbaren,
  OpenAI-kompatiblen Endpoint und kodiert keine Schlüssel oder Modellnamen.
- Europäisch/on-prem anschlussfähig: Der Prüfer kann an BRZ-LLMaaS gehängt werden.
- Fail-closed: Fehlende Quellen, unparsebare Judge-Antworten und Transportfehler
  führen nicht zur Auslieferung einer ungedeckten Antwort.
- Quellenbindung: Der Judge soll ausschließlich aus den Quellen entscheiden und
  kein Vorwissen verwenden.
- Fragekontext: Kurze Antworten werden relativ zur ursprünglichen Frage prüfbar.

## Was vor dem BRZ-Hintergrund fehlt

1. Kein expliziter Eingangsmechanismus.
   Es gibt noch kein `CalibrateState` vor Retrieval und Generation.

2. Quellen sind noch rohe Strings.
   Für ida braucht es `SourcePacket` mit URL, Domain, Stand, Abrufzeit,
   Quellentyp, Autoritätsstufe und Gültigkeits-/Freshness-Status.

3. Der offizielle Scope ist breiter als der aktuelle Prototyp.
   BRZ beschreibt Wissensbasen aus `oesterreich.gv.at` und `id-austria.gv.at`.
   Der Prototyp testet bisher primär den ID-Austria-FAQ-Ausschnitt. Das ist als
   Pilot gut, darf aber nicht als vollständige ida-Abdeckung behauptet werden.

4. Unabhängigkeit des Prüfers muss technisch präzisiert werden.
   Ideal ist ein separater Judge-Deploymentpfad. Wenn Generator und Judge dasselbe
   Modell nutzen, braucht es mindestens getrennte Rollen, Prompts, Logging und
   Metriken; sonst ist „unabhängig“ nur eingeschränkt belastbar.

5. Quellenanzeige muss Teil des OutputContracts werden.
   BRZ beschreibt Quellenangaben und sichtbare URLs. Das Gate sollte deshalb nicht
   nur `allow/block` liefern, sondern auch sagen, welche Quellen die ausgelieferte
   Antwort tragen.

6. Feedback und Fehlerlernen fehlen noch.
   Da ida negatives Feedback abfragt, sollte dieses in redigierte
   NegativeEvidence-Fälle und Regressionstests überführt werden.

7. Datenschutz und Speicherfristen müssen ins Audit-Design.
   BRZ nennt serverseitige Speicherung und Löschung nach 90 Tagen. Das lokale
   Audit-Log ist nur ein Prototyp; produktiv braucht es Reduktion, Redaktion,
   Fristen und Zweckbindung.

## Wertekarte und Gradienten in dieser Architektur

Die Wertekarte ist keine Faktenprüfmaschine. Sie gehört oberhalb des Gates als
Governance- und Produktkompass:

- Wahrheitstreue
- Quellenbindung
- Zurückhaltung bei Unsicherheit
- Zuständigkeitsklarheit
- Datenschutz
- Nachvollziehbarkeit
- Bürgerinnen und Bürger nicht irreführen

Gradienten bleiben interne Risikoklassen:

| Intern | Externes Wording | Bedeutung |
|---|---|---|
| Gradient 2 | Standard | einfache FAQ-/Hilfefrage mit Quellen |
| Gradient 3 | streng | Fristen, Gebühren, Zuständigkeiten, rechtlich relevante Orientierung |
| Gradient 4 | kritisch | Hot Facts, Nutzerwiderspruch, tagesaktuelle Amtsträger, Reputationsrisiko |

Für Nutzerinnen und Nutzer sollte nicht „Gradient“ sichtbar sein. Sichtbar ist nur
das Verhalten: präzisere Rückfrage, strengere Quellenwahl, vorsichtigere Antwort
oder Block mit sauberer Begründung.

## Konsequenz für den nächsten Schritt

Nicht sofort ein großes Framework bauen. Der kleine, BRZ-kompatible nächste Schritt:

1. `CalibrateState` als Dataclass ergänzen.
2. Eine einfache `calibrate(question)`-Funktion bauen.
3. `SourcePacket` statt `list[str]` vorbereiten, aber Kompatibilität zu `list[str]`
   behalten.
4. Ein Testset für sichtbare Nachfragen ergänzen:
   - keine Nachfrage bei klarer FAQ-Frage
   - Nachfrage bei mehrdeutiger ID-Austria-Frage
   - Block oder Hot-Fact-Route bei tagesaktueller politischer Frage
5. `GroundingResult` später um `DriftReport` und tragende Quellen erweitern.

Damit bleibt Dejans Gate schlank, aber es wird an die tatsächliche BRZ-Architektur
angeschlossen: CalibrateState als Eingangssicherheit, Grounding-Gate als
Ausgangssicherheit.
