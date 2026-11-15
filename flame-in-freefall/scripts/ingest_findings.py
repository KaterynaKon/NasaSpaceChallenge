#!/usr/bin/env python3
"""
Ingest the team's filled spreadsheet into data/findings.json.

Notes on quality:
- the submitted summaries are complete sentences, so nothing is trimmed;
- PSI-100 has no source at all (the cell literally says "No DOI found but
  here's key findings based on the experiment preview"), so it is stored but
  flagged unverified and kept out of the product until a source is added.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

UNVERIFIED_MARKERS = (
    "no doi found",
    "based on the experiment preview",
    "i could not",
    "not found but",
)


def clean(text):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    return text


def is_unverified(text, links):
    low = text.lower()
    if not links:
        return True
    return any(marker in low for marker in UNVERIFIED_MARKERS)


def normalize_doi(raw):
    raw = raw.strip().rstrip(".,;)")
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw)
    return raw


def main():
    raw = json.load(open(os.path.join(DATA, "findings_raw.json"), encoding="utf-8"))
    out = {}
    for row in raw:
        text = clean(row.get("findings"))
        links = []
        for link in row.get("links") or []:
            link = link.strip().rstrip(".,")
            if link and link not in links:
                links.append(link)
        dois = []
        for d in row.get("dois") or []:
            d = normalize_doi(d)
            if d and d not in dois:
                dois.append(d)

        unverified = is_unverified(text, links)
        out[row["id"]] = {
            "summary": text,
            "links": links[:6],
            "dois": dois[:6],
            "verified": not unverified,
            "source": "team",
            "table_downloaded": row.get("table_downloaded"),
        }

    path = os.path.join(DATA, "findings.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    for k, v in out.items():
        flag = "ok" if v["verified"] else "UNVERIFIED"
        print(f"{k:8} {len(v['summary']):4} chars | links {len(v['links']):2} | dois {len(v['dois']):2} | {flag}")
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
