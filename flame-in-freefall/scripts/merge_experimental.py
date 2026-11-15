#!/usr/bin/env python3
"""
Merge parsed Experimental table data into the main dataset and the handoff CSV.

Inputs : data/investigations.json, data/physics.json, data/experimental/*.json
Outputs: data/investigations.json (adds "experimental" block)
         data/physics.json        (numbers from tables override text extraction)
         handoff/to_fill.csv      (numeric columns filled where known)
"""

import csv
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CSV_PATH = os.path.join(ROOT, "handoff", "to_fill.csv")


def load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    investigations = load(os.path.join(DATA, "investigations.json"), [])
    physics = {r["id"]: r for r in load(os.path.join(DATA, "physics.json"), [])}
    by_id = {r["id"]: r for r in investigations}

    merged = 0
    for path in sorted(glob.glob(os.path.join(DATA, "experimental", "*.json"))):
        exp = load(path, None)
        if not exp:
            continue
        acc = exp["id"]
        rec = by_id.get(acc)
        if not rec:
            print(f"skip {acc}: not in investigations.json")
            continue

        combined = exp["combined"]
        rows = sum(f["rows"] for f in exp["files"])
        rec["experimental"] = {
            "files": [f["file"] for f in exp["files"]],
            "rows": rows,
            "o2_pct": combined["o2_pct"],
            "pressure_psia": combined["pressure_psia"],
            "flow_cm_s": combined["flow_cm_s"],
            "size_mm": combined["size_mm"],
            "kind": exp["files"][0].get("kind", "per_test") if exp["files"] else "per_test",
        }

        phys = physics.get(acc)
        if phys:
            if combined["o2_pct"]:
                phys["atmosphere"]["o2_percent_min"] = combined["o2_pct"][0]
                phys["atmosphere"]["o2_percent_max"] = combined["o2_pct"][1]
                phys["atmosphere"]["source"] = "experimental_table"
            if combined["pressure_psia"]:
                phys["atmosphere"]["pressure_psia_min"] = combined["pressure_psia"][0]
                phys["atmosphere"]["pressure_psia_max"] = combined["pressure_psia"][1]
            if combined["flow_cm_s"]:
                phys["flow"]["velocity_cm_s_min"] = combined["flow_cm_s"][0]
                phys["flow"]["velocity_cm_s_max"] = combined["flow_cm_s"][1]
                phys["flow"]["source"] = "experimental_table"
            if combined["size_mm"]:
                phys["fuel"]["size_mm"] = combined["size_mm"]
            phys["experimental_rows"] = rows
        merged += 1
        print(f"{acc:8} merged: rows={rows} O2={combined['o2_pct']} P={combined['pressure_psia']}")

    with open(os.path.join(DATA, "investigations.json"), "w", encoding="utf-8") as fh:
        json.dump(investigations, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "physics.json"), "w", encoding="utf-8") as fh:
        json.dump(list(physics.values()), fh, ensure_ascii=False, indent=1)

    # refresh numeric columns in the handoff CSV
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames
            rows_csv = list(reader)

        for row in rows_csv:
            exp = by_id.get(row["id"], {}).get("experimental")
            if not exp:
                continue
            if exp["o2_pct"]:
                row["o2_min_pct"] = f"{exp['o2_pct'][0]:g}"
                row["o2_max_pct"] = f"{exp['o2_pct'][1]:g}"
            if exp["pressure_psia"]:
                row["pressure_psia"] = f"{exp['pressure_psia'][0]:g}-{exp['pressure_psia'][1]:g}"
            if exp["flow_cm_s"]:
                row["flow_min_cm_s"] = f"{exp['flow_cm_s'][0]:g}"
                row["flow_max_cm_s"] = f"{exp['flow_cm_s'][1]:g}"
            if exp["size_mm"]:
                row["specimen_size_mm"] = f"{exp['size_mm'][0]:g}-{exp['size_mm'][1]:g}"
            row["prefilled_evidence"] = (
                f"Experimental table: {exp['rows']} tests, "
                f"{len(exp['files'])} file(s). Numbers computed by parser."
            )
            row["status"] = "numbers_done" if row["key_findings"] else "needs_findings"

        with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows_csv)

    print(f"\nmerged investigations: {merged}")


if __name__ == "__main__":
    main()
