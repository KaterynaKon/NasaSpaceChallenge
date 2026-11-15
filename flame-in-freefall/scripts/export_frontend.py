#!/usr/bin/env python3
"""
Export the dataset in the shape the Next.js frontend expects.

The frontend was scaffolded against a hand-written mock, so this adapter keeps
its field names (name, fullName, score, breakdown) and adds the full per-
environment scores under `scores` for components that want them.

Inputs : data/dashboard_data.json, data/detail/PSI-*.json, data/findings.json
Output : data/dashboard_data.frontend.json
"""
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def year_of(value):
    m = re.search(r"(19|20)\d{2}", str(value or ""))
    return int(m.group()) if m else None


def years_of(detail):
    start = year_of(detail.get("investigationStartDate"))
    end = year_of(detail.get("investigationEndDate"))
    if start and end and start != end:
        return f"{start}\u2013{end}", start
    return (str(start) if start else ""), start


IMAGES_PATH = os.path.join(DATA, "images.json")


def load_images():
    if not os.path.exists(IMAGES_PATH):
        return {}
    return json.load(open(IMAGES_PATH, encoding="utf-8"))


def main():
    images = load_images()
    dash = json.load(open(os.path.join(DATA, "dashboard_data.json"), encoding="utf-8"))
    findings = json.load(open(os.path.join(DATA, "findings.json"), encoding="utf-8"))
    detail = {}
    for path in glob.glob(os.path.join(DATA, "detail", "PSI-*.json")):
        rec = json.load(open(path, encoding="utf-8"))
        detail[rec["accession"]] = rec

    raw = {r["id"]: r for r in json.load(open(os.path.join(DATA, "investigations.json"), encoding="utf-8"))}
    out = []
    for rec in dash["investigations"]:
        phys = rec.get("physics") or {}
        exp = rec.get("experimental") or {}
        det = detail.get(rec["id"], {})
        parts = {p["label"]: p for p in rec["scores"]["cabin"]["parts"]}

        def pct(label):
            part = parts.get(label)
            return round(part["points"] / part["max"] * 100) if part and part["max"] else 0

        o2 = phys.get("o2") or [None, None]
        lo, hi = (o2 + [None, None])[:2]
        if lo is None and hi is None and exp.get("o2"):
            lo, hi = exp["o2"]
        if lo is not None and hi is not None:
            o2_label = f"{lo:g}\u2013{hi:g}%"
        elif hi:
            o2_label = f"\u2264 {hi:g}%"
        elif lo:
            o2_label = f"\u2265 {lo:g}%"
        else:
            o2_label = "not stated"

        pr = phys.get("pressure") or [None, None]
        plo, phi = (pr + [None, None])[:2]
        if plo is None and phi is None and exp.get("pressure"):
            plo, phi = exp["pressure"]
        if plo is not None and phi is not None:
            pressure_label = f"{plo:g} psia" if abs(plo - phi) < 0.05 else f"{plo:g}\u2013{phi:g} psia"
        elif phi:
            pressure_label = f"\u2264 {phi:g} psia"
        elif plo:
            pressure_label = f"\u2265 {plo:g} psia"
        else:
            pressure_label = "not stated"

        flow = phys.get("flow") or [None, None]
        flow_max = flow[1] if len(flow) > 1 else None
        years, year = years_of(det)

        found = findings.get(rec["id"])
        cards = []
        if found and found.get("verified"):
            cards.append({
                "text": found["summary"],
                "source": "Compiled from PSI publications",
                "doi": (found.get("dois") or [""])[0],
                "url": (found.get("links") or [""])[0],
            })

        pubs = [{
            "title": p.get("title") or "",
            "venue": p.get("journal") or p.get("conference") or "NASA PSI",
            "year": p.get("year") or "",
            "citations": 0,
            "openAccess": True,
            "url": ("https://doi.org/" + p["doi"]) if p.get("doi") else (det.get("sourceLink") or ""),
        } for p in (det.get("publications") or [])[:4]]

        exp_nums = bool(exp and (exp.get("o2") or exp.get("pressure") or exp.get("flow")))
        if exp_nums:
            badge = "table parsed"
        elif exp:
            badge = "samples only"
        elif (phys.get("o2") or [None, None])[1] or (phys.get("pressure") or [None, None])[1]:
            badge = "from report"
        else:
            badge = "estimated"

        hw_raw = (raw.get(rec["id"]) or {}).get("hardware")
        if isinstance(hw_raw, dict):
            hw_name, hw_url = hw_raw.get("name") or "not stated", hw_raw.get("link") or ""
        else:
            hw_name, hw_url = (rec.get("hardware") or hw_raw or "not stated"), ""

        out.append({
            "id": rec["id"],
            "badge": badge,
            "name": rec.get("acronym") or rec["id"],
            "fullName": rec.get("title") or "",
            "category": rec.get("sub_area") or "",
            "platform": rec.get("platform") or "",
            "years": years,
            "year": year,
            "fuelTypes": phys.get("fuel") or [],
            "testedMaterials": phys.get("materials") or [],
            "fuelLabel": ", ".join(phys.get("fuel") or []).capitalize(),
            "o2Label": o2_label,
            "o2Max": hi,
            "flowLabel": f"\u2264 {flow_max:g} cm/s" if flow_max else "n/a",
            "pressureLabel": pressure_label,
            "hardware": {
                "name": hw_name,
                "url": hw_url,
            },
            "dataFiles": {
                "count": (rec.get("files") or {}).get("count") or 0,
                "sizeGb": round((rec.get("files") or {}).get("size_gb") or 0, 1),
            },
            "samples": exp.get("rows") or 0,
            "tags": (rec.get("keywords") or [])[:3] + ([f"{o2_label} O\u2082"] if hi else []),
            "score": rec["scores"]["cabin"]["score"],
            "scoreParts": {
                env: [{"label": x["label"], "points": x["points"],
                       "max": x["max"], "why": x["why"]} for x in rec["scores"][env]["parts"]]
                for env in rec["scores"]
            },
            "scores": {k: v["score"] for k, v in rec["scores"].items()},
            "findings": cards,
            "publications": pubs,
            "sourceUrl": rec.get("source_url"),
            "image": (images.get(rec["id"]) or {}).get("file"),
            "imageCaption": (images.get(rec["id"]) or {}).get("caption"),
        })

    path = os.path.join(DATA, "dashboard_data.frontend.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {path}: {len(out)} records, {os.path.getsize(path)/1024:.0f} KB")


if __name__ == "__main__":
    main()
