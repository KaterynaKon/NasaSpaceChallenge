#!/usr/bin/env python3
"""
Parse NASA PSI "Experimental table" CSVs into normalized test conditions.

The tables are not standardized: every investigation names its columns
differently and mixes units (mole fraction vs %, atm vs psia, mm/s vs cm/s).
This script detects columns by keyword, reads the unit from the header, and
computes min/max ranges per investigation.

Usage:
    python3 scripts/parse_experimental_tables.py <folder-with-csvs>

File names must start with the accession, e.g.
    PSI-10_Experimentaltable_FlameDesign_InverseFlame.csv
Several files per investigation are allowed; ranges are merged.

Output: data/experimental/<ACCESSION>.json
"""

import csv
import glob
import json
import os
import re
import sys

ATM_TO_PSIA = 14.6959
KPA_TO_PSIA = 0.145038
MPA_TO_PSIA = 145.038
BAR_TO_PSIA = 14.5038

O2_KEYS = ("xo2", "o2", "oxygen", "o2conc", "o2fraction", "o2molefraction")
P_KEYS = ("pmean", "pressure", "press", "chamberpressure", "pinit", "ptot")
FLOW_KEYS = ("velocity", "flow", "airflow", "speed", "uinf", "vgas")
SIZE_KEYS = ("thickness", "diameter", "length", "width", "size", "dimension")


def to_float(value):
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def header_unit(header):
    """Pull a unit out of a column header like 'pmean (atm)' or 'velocity, cm/s'."""
    match = re.search(r"[\(\[]([^\)\]]+)[\)\]]", header)
    if match:
        return match.group(1).strip().lower()
    match = re.search(r",\s*([a-zA-Z/%]+)\s*$", header)
    return match.group(1).strip().lower() if match else ""


def pick(headers, keys, exclude=()):
    """First header whose normalized name contains one of the keys."""
    for header in headers:
        low = header.lower()
        if any(bad in low for bad in exclude):
            continue
        if any(key in low for key in keys):
            return header
    return None


def pick_preferred(headers, ordered_keys, exclude=()):
    """Like pick(), but respects priority order of the keys (pmean before pinit)."""
    usable = [h for h in headers if not any(bad in h.lower() for bad in exclude)]
    for key in ordered_keys:
        for header in usable:
            if key in header.lower():
                return header
    return None


def o2_to_percent(value, header):
    """Mole fraction -> %, percent stays as is."""
    if value is None:
        return None
    unit = header_unit(header)
    if "%" in unit or "percent" in unit:
        return value
    if "ppm" in unit:
        return value / 1e4
    # XO2 and similar are fractions
    return value * 100 if value <= 1.5 else value


def pressure_to_psia(value, header):
    if value is None:
        return None
    unit = header_unit(header)
    if "atm" in unit:
        return value * ATM_TO_PSIA
    if "kpa" in unit:
        return value * KPA_TO_PSIA
    if "mpa" in unit:
        return value * MPA_TO_PSIA
    if "bar" in unit:
        return value * BAR_TO_PSIA
    if "psia" in unit or "psi" in unit:
        return value
    if "torr" in unit or "mmhg" in unit:
        return value * 0.0193368
    return value


def flow_to_cm_s(value, header):
    if value is None:
        return None
    unit = header_unit(header)
    if "mm/s" in unit:
        return value / 10
    if "m/s" in unit:
        return value * 100
    if "cm/s" in unit:
        return value
    return value


def size_to_mm(value, header):
    if value is None:
        return None
    unit = header_unit(header)
    if "cm" in unit and "mm" not in unit:
        return value * 10
    if "m" == unit:
        return value * 1000
    return value


def parse_file(path):
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.DictReader(fh, dialect=dialect))

    if not rows:
        return None

    headers = list(rows[0].keys())
    headers = [h for h in headers if h]

    o2_col = pick(headers, O2_KEYS)
    p_col = pick_preferred(headers, P_KEYS, exclude=("partial", "po2"))
    # some tables leave the mean pressure blank for part of the rows; fall back
    # to the initial pressure so those tests are not silently dropped
    p_fallback = pick_preferred(headers, ("pinit", "pressure", "press"), exclude=("partial", "po2"))
    if p_fallback == p_col:
        p_fallback = None
    flow_col = pick(headers, FLOW_KEYS)
    size_col = pick(headers, SIZE_KEYS)

    o2_values, p_values, flow_values, size_values = [], [], [], []
    for row in rows:
        if o2_col:
            v = o2_to_percent(to_float(row.get(o2_col)), o2_col)
            if v is not None and 0 < v <= 100:
                o2_values.append(v)
        if p_col:
            raw = to_float(row.get(p_col))
            col = p_col
            if raw is None and p_fallback:
                raw = to_float(row.get(p_fallback))
                col = p_fallback
            v = pressure_to_psia(raw, col)
            if v is not None and 0 < v < 1000:
                p_values.append(v)
        if flow_col:
            v = flow_to_cm_s(to_float(row.get(flow_col)), flow_col)
            if v is not None and 0 <= v < 10000:
                flow_values.append(v)
        if size_col:
            v = size_to_mm(to_float(row.get(size_col)), size_col)
            if v is not None and 0 < v < 10000:
                size_values.append(v)

    def rng(values, nd=2):
        if not values:
            return None
        return [round(min(values), nd), round(max(values), nd)]

    return {
        "file": os.path.basename(path),
        "rows": len(rows),
        "columns": headers,
        "detected": {"o2": o2_col, "pressure": p_col, "flow": flow_col, "size": size_col},
        "o2_pct": rng(o2_values),
        "pressure_psia": rng(p_values),
        "flow_cm_s": rng(flow_values),
        "size_mm": rng(size_values),
        "counts": {"o2": len(o2_values), "pressure": len(p_values),
                   "flow": len(flow_values), "size": len(size_values)},
    }


def merge(results):
    def combine(key):
        vals = [r[key] for r in results if r[key]]
        if not vals:
            return None
        return [min(v[0] for v in vals), max(v[1] for v in vals)]

    return {
        "o2_pct": combine("o2_pct"),
        "pressure_psia": combine("pressure_psia"),
        "flow_cm_s": combine("flow_cm_s"),
        "size_mm": combine("size_mm"),
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    folder = sys.argv[1]
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "data", "experimental")
    os.makedirs(out_dir, exist_ok=True)

    by_acc = {}
    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        name = os.path.basename(path)
        match = re.match(r"(PSI-\d+)", name, re.IGNORECASE)
        if not match:
            print(f"skip (no accession): {name}")
            continue
        acc = match.group(1).upper()
        parsed = parse_file(path)
        if parsed is None:
            continue
        by_acc.setdefault(acc, []).append(parsed)
        print(f"{acc:8} {name[:60]:60} rows={parsed['rows']:4} "
              f"O2={parsed['o2_pct']} P={parsed['pressure_psia']} "
              f"flow={parsed['flow_cm_s']}")

    for acc, results in by_acc.items():
        payload = {"id": acc, "files": results, "combined": merge(results)}
        path = os.path.join(out_dir, f"{acc}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"\ninvestigations parsed: {len(by_acc)} -> {out_dir}")


if __name__ == "__main__":
    main()
