#!/usr/bin/env python3
"""Harvester für die ida-Wissensbasis (ida-Kern).

Zieht die FAQ-Seiten aus dem Bereich `hilfe-zu-ida` + `hilfe-zur-app-ida` von
id-austria.gv.at und normalisiert sie zu Frage→Antwort→Quelle-Tripeln.

Dependency-frei (nur stdlib). Vorgehen (siehe harvest/README.md):
  1. sitemap.xml laden, auf ida-Kern-URLs filtern, lastmod je URL merken.
  2. Jede Seite höflich (~0.5 Req/s, User-Agent) holen, Roh-HTML sichern.
  3. FAQ-Blöcke extrahieren: <h2 id="header-…"> = Frage, folgende Absätze = Antwort.
  4. Zu FAQItem normalisieren (stand = lastmod aus Sitemap).
  5. Ablage: data/faq/ida_faq.jsonl + .csv, Roh-HTML nach data/raw/.

Aufruf:  python3 harvest/harvest.py
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean import clean_items  # noqa: E402  (gemeinsame Bereinigungsregeln)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
FAQ_DIR = ROOT / "data" / "faq"

SITEMAP = "https://www.id-austria.gv.at/sitemap.xml"
# ida-Kern: nur diese beiden Bereiche.
CORE_PREFIXES = (
    "https://www.id-austria.gv.at/de/hilfe/hilfe-zu-ida/",
    "https://www.id-austria.gv.at/de/hilfe/hilfe-zur-app-ida/",
)
USER_AGENT = "idaverbesserung-faq-harvester/0.1 (research; grounding-gate)"
DELAY_S = 0.5

_H2 = re.compile(
    r'<h2\s+id="header-[^"]*"[^>]*>(.*?)</h2>(.*?)(?=<h2\b|</main\b|<footer\b|$)',
    re.IGNORECASE | re.DOTALL,
)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted gov host)
        return resp.read().decode("utf-8", errors="replace")


def _strip(fragment: str) -> str:
    text = _TAG.sub(" ", fragment)
    text = html.unescape(text)
    return _WS.sub(" ", text).strip()


def load_core_urls() -> list[tuple[str, str]]:
    """(url, lastmod) für alle ida-Kern-Seiten aus dem Sitemap."""
    xml = _fetch(SITEMAP)
    entries: list[tuple[str, str]] = []
    for block in re.findall(r"<url>(.*?)</url>", xml, re.DOTALL):
        loc = re.search(r"<loc>(.*?)</loc>", block)
        if not loc:
            continue
        url = loc.group(1).strip()
        if not url.startswith(CORE_PREFIXES):
            continue
        lm = re.search(r"<lastmod>(.*?)</lastmod>", block)
        lastmod = (lm.group(1).strip()[:10] if lm else "")
        entries.append((url, lastmod))
    return sorted(set(entries))


def parse_faq(html_text: str, url: str, lastmod: str) -> list[dict]:
    """FAQ-Blöcke einer Seite → Liste von FAQItem-dicts."""
    kategorie = url.split("/de/hilfe/")[-1].split("/")[0]
    items: list[dict] = []
    for q_frag, a_frag in _H2.findall(html_text):
        frage = _strip(q_frag)
        antwort = _strip(a_frag)
        if len(frage) < 5 or len(antwort) < 5:
            continue
        items.append({
            "frage": frage,
            "antwort": antwort,
            "quelle_url": url,
            "kategorie": kategorie,
            "stand": lastmod,
        })
    return items


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FAQ_DIR.mkdir(parents=True, exist_ok=True)

    print("Lade Sitemap …", file=sys.stderr)
    urls = load_core_urls()
    print(f"ida-Kern-Seiten im Sitemap: {len(urls)}", file=sys.stderr)

    all_items: list[dict] = []
    pages_with_faq = 0
    for i, (url, lastmod) in enumerate(urls, 1):
        slug = url.rstrip("/").split("/")[-1] or "index"
        try:
            page = _fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{len(urls)}] FEHLER {url}: {exc}", file=sys.stderr)
            continue
        (RAW_DIR / f"{slug}.html").write_text(page, encoding="utf-8")
        items = parse_faq(page, url, lastmod)
        if items:
            pages_with_faq += 1
        all_items.extend(items)
        print(f"  [{i}/{len(urls)}] {slug}: {len(items)} FAQ", file=sys.stderr)
        time.sleep(DELAY_S)

    # Bereinigung + Klassifikation (gemeinsame Regeln aus clean.py).
    roh = len(all_items)
    all_items, report = clean_items(all_items)
    print(f"Bereinigung: {json.dumps(report, ensure_ascii=False)}", file=sys.stderr)

    fields = ["frage", "antwort", "quelle_url", "kategorie", "stand", "ist_frage"]

    jsonl = FAQ_DIR / "ida_faq.jsonl"
    with jsonl.open("w", encoding="utf-8") as fh:
        for item in all_items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    csv_path = FAQ_DIR / "ida_faq.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_items)

    fragen = sum(1 for it in all_items if it["ist_frage"])
    print(
        f"\nFertig: {len(all_items)} bereinigte Tripel ({fragen} Fragen) "
        f"aus {roh} Roh-Blöcken / {pages_with_faq}/{len(urls)} Seiten.\n"
        f"  → {jsonl.relative_to(ROOT)}\n  → {csv_path.relative_to(ROOT)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
