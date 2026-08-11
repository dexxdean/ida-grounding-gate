# Datenbeschaffung (Harvest)

Ziel: eine **Ground-Truth-Wissensbasis** als Frage→Antwort→Quelle-Tripel aus den
öffentlichen gov.at-FAQ-Seiten, die ida selbst als Wissensbasis nutzt.

## Was NICHT verfügbar ist

Die **4.600 Testfragen** aus ida's Testphase sind **nicht öffentlich** (internes
Experten-Testing laut BKA/OTS-Aussendung vom 10.08.2026). Kein Open-Data-Release,
kein Zenodo, kein data.gv.at-Datensatz. → Diese Fragen können wir nicht ziehen.

## Was VERFÜGBAR ist (gefunden 10.08.2026)

Die FAQ-/Hilfe-Seiten sind öffentlich und strukturiert (Frage + Antwort + Quelle).
Bereich „Hilfe zu ida" auf id-austria.gv.at; klassische `haeufige-fragen` auf
oesterreich.gv.at (leiten teils auf id-austria.gv.at um).

Bestätigte Einstiegspunkte:

- https://www.id-austria.gv.at/hilfe/hilfe-zu-ida/generelle-info
- https://www.id-austria.gv.at/de/hilfe/hilfe-zu-ida/registrierung
- https://www.id-austria.gv.at/de/hilfe/hilfe-zu-ida/authentifizierungsfaktoren
- https://www.id-austria.gv.at/de/hilfe/hilfe-zu-ida/id-austria-zertifikat
- https://www.id-austria.gv.at/de/hilfe
- https://www.oesterreich.gv.at/id-austria/haeufige-fragen/registrierung.html
- https://www.oesterreich.gv.at/eausweise/haeufige-fragen/...

Hinweis: Viele oesterreich.gv.at-URLs antworten mit **301-Redirect** auf
id-austria.gv.at — der Harvester muss Redirects folgen.

## Verfahren — geklärt per Stichprobe (10.08.2026)

Entscheidung getroffen: **Umfang = alle ID-Austria-FAQ**, **Methode = httpx-Skript**
(kein Browser nötig). Begründung aus der Stichprobe:

- **Discovery über `sitemap.xml`.** `https://www.id-austria.gv.at/sitemap.xml`
  listet **126 `/hilfe/`-Seiten** vollständig — die JS-gerenderte Navigation
  muss also gar nicht gecrawlt werden. robots.txt erlaubt `/de/hilfe/*`
  (gesperrt sind nur `/.search/`, `/Portal.Node/`, `/testordner*`, `/.syndication/`).
- **Inhalt rendert serverseitig.** Roh-`curl` liefert die FAQ-Texte; die Fragen
  stehen als `<h2 id="header-<frage-slug>-<hash>">`, die Antworten im zugehörigen
  Accordion-Panel. → einfaches HTML-Parsing genügt, kein JS-Renderer.
- **`lastmod` je Seite vorhanden** → füllt das `stand`-Feld automatisch. Das ist
  direkt die Gegenmaßnahme zum „2024-Daten"-Fehlertyp.

### Gewählter Umfang: ida-Kern (45 eindeutige Seiten)

| Bereich             | Seiten (Sitemap) |
|---------------------|-----------------:|
| `hilfe-zu-ida`      | 30               |
| `hilfe-zur-app-ida` | 15               |

(Die App-Bereiche `eausweise`/`eausweis-check` sind bewusst ausgeklammert.)

**Bewusste Verengung ggü. ida:** ida nutzt laut BRZ geprüfte Inhalte von
**oesterreich.gv.at UND id-austria.gv.at** (siehe `docs/ida-fakten.md`). Wir
harvesten nur den **id-austria.gv.at-Kern**. Für ein Gate-/Eval-Prototyp genügt
dieser abgegrenzte, in sich konsistente Ausschnitt; er ist aber **nicht** die
vollständige ida-Wissensbasis. Der breitere oesterreich.gv.at-Bestand (u. a.
allgemeine Verwaltungsthemen) bleibt für später — das ist beim Interpretieren der
Eval-Zahlen mitzudenken.

### Pipeline (ausgeführt)

`harvest/harvest.py`:
1. `sitemap.xml` laden, auf ida-Kern-URLs filtern, `lastmod` je URL merken.
2. Jede Seite per stdlib-`urllib` holen (robots-konform, ~0,5 Req/s, User-Agent),
   Roh-HTML nach `data/raw/` sichern.
3. FAQ-Blöcke extrahieren: `<h2 id="header-…">` = Frage, Folgeinhalt bis zur
   nächsten `<h2>` = Antwort.
4. `clean.clean_items(...)` anwenden (Regeln unten), `stand` = `lastmod`.
5. Ablage: `data/faq/ida_faq.jsonl` + `.csv` (Feld `ist_frage` inklusive).

**Ergebnis:** 170 Roh-Blöcke → **158 bereinigte Tripel** (126 echte Fragen,
32 Abschnitts-Überschriften) aus 44/45 Seiten. Rohfassung gesichert als
`data/faq/ida_faq.raw.jsonl`.

### Bereinigungsregeln (`harvest/clean.py`)

Aus einem Audit der echten Daten abgeleitet, alle idempotent und getestet:

- **N1** Leerzeichen-Artefakte aus leeren Inline-Tags: `SMS - TAN` → `SMS-TAN`,
  `FIDO -Schlüssel` → `FIDO-Schlüssel`, `E -Mail` → `E-Mail`.
- **N2** Leerzeichen vor Satzzeichen: `App ?` → `App?`.
- **N3** Leerzeichen in typografischen Anführungszeichen: `„ ID` → `„ID`.
- **N4** Domain-Tippfehler der Quelle: `osterreich.gv.at` → `oesterreich.gv.at`.
- **N5** Mehrfach-Leerzeichen → eines, trimmen.
- **D1** Reine Kontakt-CTA („Bitte kontaktieren Sie das Service Center.") entfernt
  (12×) — kein Wissenswert.
- **D2** Exakte Duplikate (Frage+Antwort) entfernt.
- **Klassifikation** `ist_frage`: True nur bei echter Nutzerfrage (endet auf `?`
  und kein generisches Struktur-Heading wie „Wann hilft mir diese Anleitung?").
  Abschnitte bleiben als Wissensbasis erhalten, werden aber nicht als Testfrage
  genutzt.

Nach der Bereinigung: 0 Spacing-Artefakte, 0 Domain-Fehler, 0 CTA-Reste,
0 Duplikate, 0 Tag-Leaks.

### Testset (ausgeführt)

`harvest/build_testset.py` nutzt nur `ist_frage=True` (dedupliziert) für positive
Fälle und ergänzt kuratierte Negativ-Fallen. **Ergebnis:** 40 Fragen
(**32 gedeckt / 8 Fallen**, inkl. „Wer ist Außenministerin?"). →
`data/testsets/testset.jsonl`.
