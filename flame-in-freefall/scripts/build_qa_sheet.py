#!/usr/bin/env python3
"""
Build a spot-check workbook for the parsed Experimental tables.

Every extreme value that feeds the dashboard is traced back to the exact row
and cell of the source CSV, so a reviewer can open the file, jump to that row
and confirm the number by eye.
"""

import csv
import glob
import os
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.properties import PageSetupProperties

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCOMING = os.path.join(ROOT, "incoming")
OUT = os.path.join(ROOT, "handoff", "QA_spotcheck.xlsx")

MMHG = 0.0193368
ATM = 14.6959
BAR = 14.5038


def read_rows(path):
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        sample = fh.read(8192)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = [r for r in csv.reader(fh, dialect)]
    return ([h.strip() for h in rows[0]], rows[1:]) if rows else ([], [])


def nums(text):
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
        if re.fullmatch(r"-?\d*\.?\d+", token):
            out.append(float(token))
    if not out:
        out = [float(m.group()) for m in re.finditer(r"-?\d*\.?\d+", t)]
    return out


def find_col(header, *needles):
    for i, h in enumerate(header):
        low = h.lower()
        if all(n in low for n in needles):
            return i
    return None


def collect(path, metrics, label_idx=0):
    """metrics: list of (name, column_index, transform, unit)"""
    header, data = read_rows(path)
    found = {name: [] for name, *_ in metrics}
    for offset, row in enumerate(data):
        excel_row = offset + 2
        label = row[label_idx].strip() if len(row) > label_idx else ""
        if not label:
            label = next((c.strip() for c in row[:4] if c and c.strip()), "")
        for name, idx, transform, unit in metrics:
            if idx is None or len(row) <= idx:
                continue
            raw = row[idx].strip()
            for v in nums(raw):
                value = transform(v)
                if value > 0:
                    found[name].append((value, label, raw, excel_row))
    return header, found


def extremes(items):
    if not items:
        return None, None
    return min(items, key=lambda x: x[0]), max(items, key=lambda x: x[0])


SPECS = []


def add(acc, acronym, pattern, builder, label_idx=0):
    SPECS.append((acc, acronym, pattern, builder, label_idx))


def b_psi25(h):
    return [("O2", find_col(h, "initial o2"), lambda v: v, "%")]


def b_psi68(h):
    return [("O2", find_col(h, "oxygen mole fraction"), lambda v: v * 100, "%"),
            ("Pressure", find_col(h, "pressure"), lambda v: v * ATM, "psia"),
            ("Flow", find_col(h, "flow velocity"), lambda v: v, "cm/s")]


def b_psi69(h):
    return [("O2", find_col(h, "o initial"), lambda v: v * 100, "%"),
            ("Pressure", find_col(h, "ambient pressure"), lambda v: v * MMHG, "psia")]


def b_saffire(h):
    return [("O2", find_col(h, "percent o2"), lambda v: v, "%"),
            ("Flow", find_col(h, "air flow"), lambda v: v, "cm/s")]


def b_psi100(h):
    return [("Flow", find_col(h, "air flow"), lambda v: v, "cm/s")]


def b_psi159(h):
    return [("O2", find_col(h, "xo2") if find_col(h, "xo2") is not None else find_col(h, "o2"), lambda v: v * 100, "%"),
            ("Pressure", find_col(h, "p", "(bar)"), lambda v: v * BAR, "psia")]


def b_psi10(h):
    o2 = find_col(h, "xo2") if find_col(h, "xo2") is not None else find_col(h, "o2")
    return [("O2", o2, lambda v: v * 100, "%"),
            ("Pressure", find_col(h, "pmean"), lambda v: v * ATM, "psia")]


add("PSI-10", "ACME/Flame Design", "PSI-10_Experimental table_Flame Design_Normal Flame.csv", b_psi10, 3)
add("PSI-10", "ACME/Flame Design", "PSI-10_Experimentaltable_FlameDesign_InverseFlame.csv", b_psi10, 2)
add("PSI-25", "BASS-II", "PSI-25*", b_psi25, 1)
add("PSI-68", "FLEX-2", "PSI-68*", b_psi68, 0)
add("PSI-69", "FLEX", "PSI-69*", b_psi69, 0)
add("PSI-98", "SAFFIRE-I", "PSI-98*", b_saffire, 0)
add("PSI-99", "SAFFIRE-II", "PSI-99*", b_saffire, 0)
add("PSI-100", "SAFFIRE-III", "PSI-100*", b_psi100, 0)
add("PSI-159", "CFI-G", "PSI-159*", b_psi159, 3)


def main():
    rows = []
    for acc, acronym, pattern, builder, label_idx in SPECS:
        for path in sorted(glob.glob(os.path.join(INCOMING, pattern))):
            header, _ = read_rows(path)
            metrics = builder(header)
            _, found = collect(path, metrics, label_idx)
            for name, items in found.items():
                unit = next((m[3] for m in metrics if m[0] == name), "")
                lo, hi = extremes(items)
                for kind, item in (("MIN", lo), ("MAX", hi)):
                    if not item:
                        continue
                    value, label, raw, excel_row = item
                    rows.append({
                        "id": acc, "acronym": acronym, "metric": name, "which": kind,
                        "file": os.path.basename(path), "excel_row": excel_row,
                        "test": label, "raw_cell": raw, "parsed": round(value, 2),
                        "unit": unit, "ok": "", "comment": "",
                    })

    wb = Workbook()
    ws = wb.active
    ws.title = "Checks"
    headers = ["id", "acronym", "metric", "min/max", "file", "excel_row", "test / sample",
               "raw value in file", "parsed", "unit", "OK?", "comment"]
    ws.append(headers)

    head_fill = PatternFill("solid", fgColor="1B2A41")
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = head_fill
        c.alignment = Alignment(vertical="center")

    keys = ["id", "acronym", "metric", "which", "file", "excel_row", "test",
            "raw_cell", "parsed", "unit", "ok", "comment"]
    for r in rows:
        ws.append([r[k] for k in keys])

    widths = [9, 20, 11, 9, 48, 10, 17, 18, 9, 8, 7, 28]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    for row in ws.iter_rows(min_row=2):
        row[10].fill = PatternFill("solid", fgColor="FFF3CD")

    ws2 = wb.create_sheet("Instructions")
    lines = [
        ("How to check this file", 14, True),
        ("", 11, False),
        ("Each row is one extreme value that feeds the dashboard.", 11, False),
        ("1. Open the CSV named in column E.", 11, False),
        ("2. Go to the row in column F (row 1 is the header, so this matches Excel's row numbers).", 11, False),
        ("3. Find the column with the same meaning as column C (O2, pressure, flow).", 11, False),
        ("4. Compare the cell to column H (raw value) and column I (what our parser produced).", 11, False),
        ("5. If they match, type OK in column K. If not, type WRONG and explain in column L.", 11, False),
        ("", 11, False),
        ("Notes", 12, True),
        ("- PSI-68 is a planned test matrix, not per-test data: its cells hold lists of values like '0.17; 0.21; 0.25'.", 11, False),
        ("- PSI-26 is not in this file: its table lists samples only, with no oxygen, pressure or flow.", 11, False),
        ("- Pressure is converted to psia; oxygen to percent by volume; flow stays in cm/s.", 11, False),
        ("- You do not need to check every row. Pick 2-3 investigations and go through them.", 11, False),
    ]
    for text, size, bold in lines:
        ws2.append([text])
        cell = ws2.cell(row=ws2.max_row, column=1)
        cell.font = Font(size=size, bold=bold)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws2.column_dimensions["A"].width = 110

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT} with {len(rows)} checks")
    for r in rows[:6]:
        print(r["id"], r["metric"], r["which"], "row", r["excel_row"], "raw", repr(r["raw_cell"]), "->", r["parsed"], r["unit"])


if __name__ == "__main__":
    main()
