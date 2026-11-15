#!/usr/bin/env python3
"""
Build normalized dataset for the Flame in Freefall dashboard
from raw NASA PSI records already downloaded.

Inputs:
  data/investigations_raw.json      - search results (24 combustion investigations)
  data/detail/PSI-*.json            - full detail records (files, publications, DOI)

Outputs:
  data/investigations.json          - 24 normalized investigation records
  data/publications.json            - unique publications with DOI, linked to investigations
  data/data_summary.json            - per-investigation file inventory summary
  data/stats.json                   - dataset-level counters
"""

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DETAIL = os.path.join(DATA, "detail")

PSI_PAGE = "https://psi.nasa.gov/physci/repo/data/investigations/{}"


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def clean(text):
    """Collapse whitespace, keep the author's wording intact."""
    if not text:
        return None
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text or None


def parse_date(value):
    """PSI gives dates as MM-DD-YYYY."""
    if not value:
        return None
    for fmt in ("%m-%d-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def split_keywords(raw):
    if not raw:
        return []
    parts = re.split(r"\s{2,}|;\s*|\|\s*", raw)
    return [p.strip() for p in parts if p.strip()]


def ext_of(name):
    _, dot, tail = name.rpartition(".")
    if not dot or len(tail) > 6:
        return "other"
    return tail.lower()


def pub_key(doi, title):
    """DOI is the stable identifier; fall back to a normalized title."""
    if doi:
        return doi.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return f"title:{slug[:120]}"


def main():
    raw = load_json(os.path.join(DATA, "investigations_raw.json"))
    search_by_id = {rec["Accession"]: rec for rec in raw["investigations"]}

    investigations = []
    publications = {}          # key -> record
    pubs_without_doi = 0

    for acc in sorted(search_by_id, key=lambda a: int(a.split("-")[1])):
        base = search_by_id[acc]
        detail_path = os.path.join(DETAIL, f"{acc}.json")
        detail = load_json(detail_path) if os.path.exists(detail_path) else {}

        hardware = base.get("Experiment Hardware") or {}
        if isinstance(hardware, str):
            hardware = {"Name": hardware, "Link": ""}

        pub_list = detail.get("publications") or []
        doi_list = []
        pub_total = 0

        for pub in pub_list:
            doi = (pub.get("doi") or "").strip()
            title = clean(pub.get("title"))
            authors_raw = pub.get("authorList") or ""
            authors = [a.strip() for a in re.split(r",\s*", authors_raw) if a.strip()]

            pub_total += 1
            if doi:
                doi_list.append(doi)
            else:
                pubs_without_doi += 1

            key = pub_key(doi, title)
            if key not in publications:
                publications[key] = {
                    "doi": doi or None,
                    "title": title,
                    "authors": authors,
                    "investigations": [acc],
                    "status": ((pub.get("status") or {}).get("annotationValue")
                               if isinstance(pub.get("status"), dict) else None),
                }
            elif acc not in publications[key]["investigations"]:
                publications[key]["investigations"].append(acc)
                if title and not publications[key]["title"]:
                    publications[key]["title"] = title

        added = detail.get("added") or []
        size_bytes = sum(f.get("file_size") or 0 for f in added)
        ext_counter = Counter(ext_of(f.get("file_name", "")) for f in added)

        record = {
            "id": acc,
            "acronym": clean(base.get("Acronym")),
            "title": clean(base.get("Title")),
            "doi": detail.get("doi") or None,
            "license": detail.get("licenseName") or None,
            "research_area": clean(base.get("Research Area")),
            "sub_area": clean(base.get("SubResearch Area")),
            "project_type": clean(base.get("Project Type")),
            "flight_platform": clean(base.get("Flight Platform")),
            "hardware": {
                "name": clean(hardware.get("Name")),
                "link": clean(hardware.get("Link")),
            },
            "start_date": parse_date(base.get("Investigation Start Date")),
            "end_date": parse_date(base.get("Investigation End Date")),
            "keywords": split_keywords(base.get("Keywords")),
            "objectives": clean(base.get("Objectives")),
            "approach": clean(base.get("Approach")),
            "hypothesis": clean(base.get("Hypothesis")),
            "impacts": clean(base.get("Research Impacts/Earth Benefits")),
            "related": [x for x in re.split(r"\s{2,}", base.get("Related Investigations") or "") if x],
            "publications": {
                "total": pub_total,
                "with_doi": len(doi_list),
                "dois": doi_list,
            },
            "publication_dois": doi_list,
            "files": {
                "count": len(added),
                "size_bytes": size_bytes,
                "size_gb": round(size_bytes / 1e9, 2),
                "by_type": dict(ext_counter.most_common(8)),
            },
            "source_url": PSI_PAGE.format(acc),
        }
        investigations.append(record)

    pub_out = sorted(publications.values(), key=lambda p: (p["doi"] is None, p["doi"] or "", p["title"] or ""))
    total_files = sum(i["files"]["count"] for i in investigations)
    total_size = sum(i["files"]["size_bytes"] for i in investigations)

    summary = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "NASA PSI (psi.nasa.gov), Combustion Science, 24 investigations",
        "investigations": [
            {
                "id": i["id"],
                "acronym": i["acronym"],
                "files": i["files"]["count"],
                "size_gb": i["files"]["size_gb"],
                "by_type": i["files"]["by_type"],
            }
            for i in investigations
        ],
    }

    stats = {
        "generated": summary["generated"],
        "investigations": len(investigations),
        "publications_listed": sum(i["publications"]["total"] for i in investigations),
        "publications_unique": len(pub_out),
        "publications_unique_with_doi": sum(1 for p in pub_out if p["doi"]),
        "publication_links_without_doi": pubs_without_doi,
        "files": total_files,
        "size_tb": round(total_size / 1e12, 2),
        "with_acronym": sum(1 for i in investigations if i["acronym"]),
        "with_own_doi": sum(1 for i in investigations if i["doi"]),
        "with_hardware": sum(1 for i in investigations if i["hardware"]["name"]),
        "with_platform": sum(1 for i in investigations if i["flight_platform"]),
        "with_publications": sum(1 for i in investigations if i["publications"]["total"]),
    }

    for name, payload in (
        ("investigations.json", investigations),
        ("publications.json", pub_out),
        ("data_summary.json", summary),
        ("stats.json", stats),
    ):
        path = os.path.join(DATA, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        print(f"wrote {name}: {os.path.getsize(path)/1024:.0f} KB")

    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
