#!/usr/bin/env python3
"""
Parse the Experimental tables the team downloaded.

The files differ in structure, so each one gets an explicit mapping instead of
guessing column names:
  PSI-25  O2 in % by volume, no pressure column
  PSI-68  a summary table of ranges, not per-test rows
  PSI-69  pressure in mmHg, O2 as mole fraction
  PSI-98  O2 written as text ranges ("21.5 - 21.7", "~ 21.5")
  PSI-99  same as PSI-98
  PSI-100 no O2 column at all
  PSI-159 numbers destroyed by an Excel round-trip -> rejected

Output: data/experimental/<id>.json in the same shape as the earlier parser.
"""

import csv
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCOMING = os.path.join(ROOT, "incoming")
OUT = os.path.join(ROOT, "data", "experimental")

MMHG_TO_PSI = 0.0193368
ATM_TO_PSI = 14.6959
BAR_TO_PSI = 14.5038


def read_rows(path):
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        sample = fh.read(8192)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(fh, dialect)
        rows = [r for r in reader]
    if not rows:
        return [], []
    header = [h.strip() for h in rows[0]]
    data = [r for r in rows[1:] if any(c.strip() for c in r)]
    return header, data


def numbers_in(text):
    """Pull every number out of a cell that may hold a range or a list."""
    if text is None:
        return []
    t = str(text)
    t = re.sub(r"(?i)(cm/s|cm|mm|mg/s|psia|atm|bar|mmhg|\bK\b|\bW\b|\bs\b|%|\bg\b)", " ", t)
    t = re.sub(r"(?i)\bor\b", ";", t)
    if re.search(r"[A-Za-z]", t):
        return []
    text = t
    t = t.replace(",", ".").replace("~", " ")
    out = []
    for token in re.split(r"[;]|\s+-\s+|–|—", t):
        token = token.strip()
        m = re.fullmatch(r"-?\d*\.?\d+", token)
        if m:
            out.append(float(token))
    if not out:
        for m in re.finditer(r"-?\d*\.?\d+", t):
            out.append(float(m.group()))
    return out


def span(values):
    # physical quantities here are strictly positive; a zero means a blank cell
    vals = [v for v in values if v is not None and v > 0]
    if not vals:
        return None
    return [round(min(vals), 4), round(max(vals), 4)]


def build(acc, files):
    combined = {"o2_pct": [], "pressure_psia": [], "flow_cm_s": [], "size_mm": []}
    for f in files:
        for key in combined:
            combined[key].extend(f.get(key) or [])
    return {
        "id": acc,
        "files": files,
        "combined": {k: span(v) for k, v in combined.items()},
    }


def parse_psi25(path):
    header, data = read_rows(path)
    i_o2 = next(i for i, h in enumerate(header) if "initial o2" in h.lower())
    i_mat = next(i for i, h in enumerate(header) if "material" in h.lower())
    o2, size, materials = [], [], set()
    for row in data:
        if len(row) <= max(i_o2, i_mat):
            continue
        for v in numbers_in(row[i_o2]):
            if 0 < v <= 100:
                o2.append(v)
        mat = row[i_mat].strip()
        if mat:
            materials.add(re.sub(r"\s+", " ", mat))
            m = re.search(r"(\d+(?:\.\d+)?)\s*micron", mat, re.I)
            if m:
                size.append(float(m.group(1)) / 1000)
    return {
        "file": os.path.basename(path),
        "rows": len(data),
        "columns": len(header),
        "mapping": {"o2": header[i_o2], "material": header[i_mat]},
        "o2_pct": span(o2),
        "pressure_psia": None,
        "flow_cm_s": None,
        "size_mm": span(size),
        "materials": sorted(materials)[:6],
        "kind": "per_test",
    }


def parse_psi68(path):
    header, data = read_rows(path)
    i_o2 = next(i for i, h in enumerate(header) if "oxygen mole fraction" in h.lower())
    i_p = next(i for i, h in enumerate(header) if "pressure" in h.lower())
    i_d = next(i for i, h in enumerate(header) if "diameter" in h.lower())
    i_f = next(i for i, h in enumerate(header) if "flow velocity" in h.lower())
    o2, p, d, fl, fuels = [], [], [], [], set()
    for row in data:
        if len(row) <= max(i_o2, i_p, i_d, i_f):
            continue
        fuels.add(row[0].strip())
        o2.extend([v * 100 for v in numbers_in(row[i_o2])])
        p.extend([v * ATM_TO_PSI for v in numbers_in(row[i_p])])
        d.extend(numbers_in(row[i_d]))
        fl.extend(numbers_in(row[i_f]))
    return {
        "file": os.path.basename(path),
        "rows": len(data),
        "columns": len(header),
        "mapping": {"o2": header[i_o2], "pressure": header[i_p], "size": header[i_d], "flow": header[i_f]},
        "o2_pct": span(o2),
        "pressure_psia": span(p),
        "flow_cm_s": span(fl),
        "size_mm": span(d),
        "materials": sorted(f for f in fuels if f)[:6],
        "kind": "matrix",
        "note": "Summary table of planned ranges, not per-test rows.",
    }


def parse_psi69(path):
    header, data = read_rows(path)
    i_o2 = next(i for i, h in enumerate(header) if h.lower().startswith("o initial"))
    i_p = next(i for i, h in enumerate(header) if "ambient pressure" in h.lower())
    i_d = next(i for i, h in enumerate(header) if "droplet initial diameter" in h.lower())
    i_fuel = next(i for i, h in enumerate(header) if h.strip().lower() == "fuel")
    o2, p, d, fuels = [], [], [], set()
    for row in data:
        if len(row) <= max(i_o2, i_p, i_d, i_fuel):
            continue
        for v in numbers_in(row[i_o2]):
            o2.append(v * 100)
        for v in numbers_in(row[i_p]):
            p.append(v * MMHG_TO_PSI)
        d.extend(numbers_in(row[i_d]))
        if row[i_fuel].strip():
            fuels.add(row[i_fuel].strip())
    return {
        "file": os.path.basename(path),
        "rows": len(data),
        "columns": len(header),
        "mapping": {"o2": header[i_o2], "pressure": header[i_p], "size": header[i_d]},
        "o2_pct": span(o2),
        "pressure_psia": span(p),
        "flow_cm_s": None,
        "size_mm": span(d),
        "materials": sorted(fuels)[:6],
        "kind": "per_test",
    }


def parse_saffire(path, has_o2=True):
    header, data = read_rows(path)
    i_o2 = next((i for i, h in enumerate(header) if "percent o2" in h.lower()), None)
    i_flow = next((i for i, h in enumerate(header) if "air flow" in h.lower()), None)
    i_mat = next((i for i, h in enumerate(header) if h.lower() == "material"), None)
    o2, flow, mats = [], [], set()
    for row in data:
        if has_o2 and i_o2 is not None and len(row) > i_o2:
            o2.extend(numbers_in(row[i_o2]))
        if i_flow is not None and len(row) > i_flow:
            flow.extend(numbers_in(row[i_flow]))
        if i_mat is not None and len(row) > i_mat and row[i_mat].strip():
            mats.add(row[i_mat].strip())
    return {
        "file": os.path.basename(path),
        "rows": len(data),
        "columns": len(header),
        "mapping": {"o2": header[i_o2] if i_o2 is not None else None,
                    "flow": header[i_flow] if i_flow is not None else None},
        "o2_pct": span(o2) if has_o2 else None,
        "pressure_psia": None,
        "flow_cm_s": span(flow),
        "size_mm": None,
        "materials": sorted(mats)[:6],
        "note": None if has_o2 else "Table has no oxygen column; only airflow is stated.",
        "kind": "per_test",
    }


def parse_psi26(path):
    """BASS table lists samples only: no oxygen, pressure or flow columns."""
    header, data = read_rows(path)
    i_mat = next((i for i, h in enumerate(header) if "material" in h.lower()), None)
    mats, sizes = set(), []
    for row in data:
        if i_mat is None or len(row) <= i_mat:
            continue
        mat = re.sub(r"\s+", " ", row[i_mat].strip())
        if mat:
            mats.add(mat)
            m = re.search(r"(\d+(?:\.\d+)?)\s*cm", mat)
            if m:
                sizes.append(float(m.group(1)) * 10)
    return {
        "file": os.path.basename(path),
        "rows": len(data),
        "columns": len(header),
        "mapping": {"material": header[i_mat] if i_mat is not None else None},
        "o2_pct": None,
        "pressure_psia": None,
        "flow_cm_s": None,
        "size_mm": span(sizes),
        "materials": sorted(mats)[:8],
        "kind": "per_test",
        "note": "Samples only; atmosphere and flow are not in this table.",
    }


def parse_psi159(path):
    """CFI-G: O2 as mole fraction, pressure in bar, gas fuels."""
    header, data = read_rows(path)
    def col(*needles):
        for i, h in enumerate(header):
            low = h.lower()
            if all(n in low for n in needles):
                return i
        return None
    i_o2 = col("xo2") if col("xo2") is not None else col("o2")
    i_p = col("p", "(bar)")
    i_fuel = col("fuel")
    o2, pr, fuels = [], [], set()
    for row in data:
        if i_o2 is not None and len(row) > i_o2:
            o2.extend([v * 100 for v in numbers_in(row[i_o2])])
        if i_p is not None and len(row) > i_p:
            pr.extend([v * BAR_TO_PSI for v in numbers_in(row[i_p])])
        if i_fuel is not None and len(row) > i_fuel and row[i_fuel].strip():
            fuels.add(row[i_fuel].strip().lower())
    return {
        "file": os.path.basename(path),
        "rows": len(data),
        "columns": len(header),
        "mapping": {"o2": header[i_o2] if i_o2 is not None else None,
                    "pressure": header[i_p] if i_p is not None else None},
        "o2_pct": span(o2),
        "pressure_psia": span(pr),
        "flow_cm_s": None,
        "size_mm": None,
        "materials": sorted(fuels)[:6],
        "kind": "per_test",
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    found = {}

    def pick(pattern):
        hits = sorted(glob.glob(os.path.join(INCOMING, pattern)))
        return hits[0] if hits else None

    specs = [
        ("PSI-25", "PSI-25*", parse_psi25),
        ("PSI-26", "PSI-26*", parse_psi26),
        ("PSI-68", "PSI-68*", parse_psi68),
        ("PSI-69", "PSI-69*", parse_psi69),
        ("PSI-98", "PSI-98*", lambda p: parse_saffire(p, True)),
        ("PSI-99", "PSI-99*", lambda p: parse_saffire(p, True)),
        ("PSI-100", "PSI-100*", lambda p: parse_saffire(p, False)),
        ("PSI-159", "PSI-159*", parse_psi159),
    ]

    for acc, pattern, fn in specs:
        paths = sorted(glob.glob(os.path.join(INCOMING, pattern)))
        if not paths:
            print(f"{acc:8} no file")
            continue
        recs = [fn(p) for p in paths]
        payload = build(acc, recs)
        with open(os.path.join(OUT, f"{acc}.json"), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        c = payload["combined"]
        rows = sum(r['rows'] for r in recs)
        print(f"{acc:8} rows {rows:4} | O2 {c['o2_pct']} | P {c['pressure_psia']} | flow {c['flow_cm_s']} | size {c['size_mm']}")
        found[acc] = True



if __name__ == "__main__":
    main()
