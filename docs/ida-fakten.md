# ida — belegte Fakten (Ground Truth für dieses Projekt)

> Zweck: damit wir nichts auf falschen Annahmen bauen. Nur öffentlich belegte
> Aussagen mit Quelle. Stand der Recherche: **2026-08-10**.
> Jede Zeile, die nicht belegt ist, ist als **Annahme** markiert.

## Was ida ist

- **Name/Definition:** „ida" = *intelligente digitale Assistenz*. Österreichs erste
  KI-Assistenz für Verwaltungsfragen. [BRZ], [OTS/Pröll]
- **Betreiber/Start:** gestartet von Digitalisierungs-Staatssekretär **Alexander
  Pröll (ÖVP)**; verfügbar **ab Ende Juli 2026**, rund um die Uhr. Öffentlicher
  Fehler-Vorfall um **2026-08-10**. [BRZ], [Heute-1]
- **Kanäle:** oesterreich.gv.at, id-austria.gv.at und in der App „ID Austria". [BRZ]
- **Themen laut BRZ:** ID-Austria-Registrierung, eAusweise, digitale Signatur,
  Wohnsitzangelegenheiten. **Nicht** im Auftrag: Tagespolitik, Regierungspersonal,
  allgemeines Weltwissen (genau dort trat der Fehler auf). [BRZ]

## Technischer Stack (belegt)

| Baustein | Beleg | Quelle |
|---|---|---|
| **LLM** | „europäisches Sprachmodell der Firma **Mistral**", **Open-Source-Version** → keine Gebühren pro Anfrage | [BRZ], [futurezone via Suche] |
| **Exakte Mistral-Variante** | **nicht öffentlich genannt** (klein/mittel/groß unbekannt) — in `judge.py` als Platzhalter `mistral-unbekannt`, NICHT als Fakt behandeln | — |
| **Hosting** | „ausschließlich in Österreich **On-Premises** in den Rechenzentren des **Bundesrechenzentrums**" | [BRZ] |
| **Plattform** | **OpenShift** Containerplattform | [BRZ] |
| **LLM-Betrieb** | **LLMaaS** (Large Language Model as a Service), BRZ-Eigenentwicklung | [BRZ] |
| **Anti-Halluzination** | **RAG-Datenbank**, „um Halluzinieren und Falschaussagen zu vermeiden" | [BRZ] |
| **Wissensquellen** | **ausschließlich geprüfte Inhalte von oesterreich.gv.at UND id-austria.gv.at** | [BRZ] |
| **Datenschutz** | keine Personalisierung, kein Profiling; Eingaben nach **90 Tagen** gelöscht; Session-Cookies **30 Min**; keine Datenweitergabe ins Ausland | [BRZ] |
| **Testphase** | **> 4.600 Testfragen** vor dem Launch | [Heute-1], [Heute-2] |

## Der Fehler-Vorfall (exakt, belegt)

Frage: „Wer ist Außenministerin?" — Ablauf laut [Heute-1]:

1. **Erste Antwort (korrekt):** Beate Meinl-Reisinger sei „Bundesministerin für
   europäische und internationale Angelegenheiten". → **stimmt tatsächlich.**
2. **Rückzieher nach FPÖ-Kritik (falsch):** ida degradierte Meinl-Reisinger zur
   „Staatssekretärin" unter „Bundesministerin Claudia Plakolm (seit 2024: Claudia
   Bauer)" und behauptete, **Karoline Edtstadler** sei die Außenministerin.
   - Edtstadler ist **ÖVP-Landeshauptfrau von Salzburg**, „nie im Außenministerium".
   - Claudia Bauer ist Europa-/Integrations-/Familienministerin, **nicht** Außen.
3. **Veraltete Daten:** ida gestand „Informationen auf einem veralteten Stand …
   laut den aktuellen Daten aus dem Jahr **2024** (sic!)" und behauptete, **Andreas
   Babler** sei „nicht mehr Vizekanzler oder Bundesminister" (falsch). [Heute-1], [Heute-2]

**Fehlertyp:** Der eigentliche Bruch war nicht die erste Antwort, sondern der
**selbstunsichere Rückzieher** auf veraltete/erfundene Fakten unter Nachfrage —
Confidence-/Temporal-/Claim-Drift, kein reines „weiß es nicht".

## Konsequenzen für unseren Build (Abgleich)

- ✅ **Testset-Falle „Außenministerin":** Halluzination in `eval/run_eval.py` von
  „Karin Kneissl" auf **„Karoline Edtstadler"** korrigiert (entspricht dem realen
  Rückzieher). Falle bleibt gültig — Regierungspersonal liegt außerhalb der
  ID-Austria-Wissensbasis; im aktuellen Testset blockt das Gate diesen Fall.
- ✅ **`judge.py` Modell:** Default von `mistral-small` auf `mistral-unbekannt`
  geändert und im Kommentar als **Annahme/Platzhalter** gekennzeichnet — die
  öffentlich nicht genannte Variante wird nicht mehr als Fakt suggeriert.
- ✅ **Harvest-Umfang:** in `harvest/README.md` als **bewusste Verengung**
  benannt — wir harvesten nur den id-austria.gv.at-Kern, ida nutzt zusätzlich
  oesterreich.gv.at.
- ℹ️ **Konzeptpapier (`docs/grounding-gate-ida.html`):** Narrativ zum
  Vorfall ist bereits **korrekt** (erst richtig, dann Rückzieher, 2024-Daten,
  Babler entfernt). Offen: optionale Präzisierung um Edtstadler/Plakolm/Bauer.

## Modell-Schätzung (Inferenz, NICHT belegt)

„Open-Source-Version" grenzt auf **offene Gewichte** ein (nicht die geschlossenen
API-Modelle wie Mistral Large). Begründetes Ranking:

1. **Mistral Small ~24B** (Apache-2.0, 2025, stark, gutes Deutsch, on-prem-freundlich)
   — passt zum ida-Launch Mitte 2026. **Top-Tipp.**
2. **Mixtral 8x7B** (MoE ~47B) — klassischer On-Prem-Griff, für 2026 eher „alt".
3. **Mistral NeMo 12B** (Apache-2.0, mehrsprachig, sparsam).

Mit hoher Wahrscheinlichkeit **kein 7B** (zu schwach für Behördenqualität).

## Lokaler Test-Befund (2026-08-10)

Der `MistralJudge` wurde lokal gegen OpenAI-kompatible Ollama-Endpoints gefahren.
Der 7B-Lauf zeigte stabilen Fallen-Recall **100 %**, aber hohe Übervorsicht
15,6 % ohne / 28,1 % mit Frage-Kontext. Das 7B blockt sogar fast wörtlich
Gedecktes und ist deshalb **kein valider Präzisions-Benchmark**.

Der stärkere Proxy-Lauf mit **Mistral NeMo 12B** ist aussagekräftiger:

| Judge / Modus | Fallen-Recall | Übervorsicht | Genauigkeit |
|---|---:|---:|---:|
| NeMo 12B, mit Frage-Kontext | 100 % | 3,1 % | 97,5 % |
| NeMo 12B, ohne Frage-Kontext | 100 % | 9,4 % | 92,5 % |

**Merke:** Frage-Kontext ist für die aktuelle Proxy-Konfiguration plausibel
entschieden (Default AN), aber die produktionsnahe Präzision muss am echten
BRZ-Endpoint bzw. einem produktionsnahen Modell gemessen werden. Fallen-Recall
= 100 % ist über die bisherigen Läufe stabil; er darf trotzdem nur auf das
aktuelle Testset bezogen werden.

## Quellen

- [BRZ] Technischer Hintergrund zu ida — https://www.brz.gv.at/presse/technischer-hintergrund-ida.html
- [OTS/Pröll] „ida – Österreichs erste KI-Assistenz …" — https://www.ots.at/presseaussendung/OTS_20260810_OTS0014/
- [Heute-1] „Neue Regierungs-KI weiß nicht, wer Außenministerin ist" — https://www.heute.at/s/neue-regierungs-ki-weiss-nicht-wer-aussenministerin-ist-120235839
- [Heute-2] „Regierungs-KI wirft Vizekanzler Babler aus Koalition" — https://www.heute.at/s/regierungs-ki-wirft-vizekanzler-babler-aus-koalition-120235983
- futurezone „ID Austria bekommt einen KI-Chatbot" (Open-Source-Mistral, keine Gebühren/Anfrage; via Suche, Artikel paywalled) — https://futurezone.at/apps/id-austria-ki-chatbot-mistral-ida-sommer-vollmacht-eausweise/403170114
