#!/usr/bin/env python3
"""
Relevance scoring for the Flame in Freefall dashboard.

Every score is a sum of five transparent components (max 100). Nothing is
hidden: the dashboard shows the breakdown per investigation, so anyone can
ask "why 72?" and get five numbers with sources.

Inputs : data/investigations.json, data/physics.json
Output : data/dashboard_data.json  (records + scores + coverage)
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# ASSUMPTIONS — target conditions are design points, not PSI measurements.
#
# cabin  14.7 psia / 21% O2 : ISS atmosphere, cited in
#        https://ntrs.nasa.gov/citations/20240003211
# habitat 8.2 psia / 34% O2 : NASA Exploration Atmosphere recommendation.
#        Revised from 8 psia / 32% to 8.2 psia / 34% to reduce hypoxia exposure.
#        The same atmosphere is planned for lunar and Martian habitats, so a
#        single "surface habitat" ranking covers both.
# suit    4.3 psia / 100% O2: EMU nominal operating pressure (30 kPa), pure O2.
#        https://www.nasa.gov/wp-content/uploads/2023/03/gernhardt-eva-ops-chp-5.4-2013.pdf
# rover   8.2 psia / 34% O2 : pressurized surface vehicle on the same exploration
#        atmosphere; liquid fuel lines add a separate hazard class.
#
# Flow targets are engineering assumptions for ventilation, not NASA requirements.
ENVIRONMENTS = [
    {
        "id": "cabin",
        "name": "Spacecraft cabin",
        "short": "ISS / orbital",
        "o2": 21, "pressure": 14.7, "flow": 20,
        "material": "solid",
        "material_class": ["fabric", "plastic"],
        "note": "Sea-level air, forced ventilation, solid materials everywhere.",
        "source": "https://ntrs.nasa.gov/citations/20240003211",
    },
    {
        "id": "habitat",
        "name": "Surface habitat",
        "short": "Moon / Mars base",
        "o2": 34, "pressure": 8.2, "flow": 10,
        "material": "solid",
        "material_class": ["fabric", "plastic"],
        "note": "NASA plans the same exploration atmosphere for lunar and Martian habitats: 8.2 psia, 34% O2. Fire risk is driven by the same O2/pressure pair, so one ranking covers both.",
        "source": "https://ntrs.nasa.gov/citations/20240003211",
    },
    {
        "id": "suit",
        "name": "Space suit",
        "short": "EVA",
        "o2": 100, "pressure": 4.3, "flow": 5,
        "material": "solid",
        "material_class": ["fabric", "plastic"],
        "note": "Pure oxygen, lowest pressure, fabric and tubing.",
        "source": "https://www.nasa.gov/wp-content/uploads/2023/03/gernhardt-eva-ops-chp-5.4-2013.pdf",
    },
    {
        "id": "rover",
        "name": "Rover / vehicle",
        "short": "Surface vehicle",
        "o2": 34, "pressure": 8.2, "flow": 40,
        "material": "liquid",
        "material_class": ["liquid"],
        "note": "Pressurized rover on the exploration atmosphere; liquid fuel lines add a separate hazard.",
        "source": "https://ntrs.nasa.gov/citations/20240003211",
    },
]

FIRE_WORDS = ("fire", "flammab", "ignit", "suppress", "extinct", "burn")


def covers(low, high, target):
    """How well a measured range covers a target value."""
    if low is None or high is None:
        return None
    if low <= target <= high:
        return "covers"
    span = max(high - low, 1)
    distance = min(abs(target - low), abs(target - high))
    if distance <= 0.1 * span + 2:
        return "near"
    return "outside"


def oxygen_points(phys, target, dataset_max=None):
    atm = (phys or {}).get("atmosphere") or {}
    low, high = atm.get("o2_percent_min"), atm.get("o2_percent_max")
    if low is None and high is None:
        return 4, "no measured O2 in PSI records", "unknown"
    if low is None:
        low = high
    if high is None:
        high = low
    state = covers(low, high, target)
    if state == "covers":
        return 35, f"documented {low:g}-{high:g}% O2 covers {target}%", "measured"
    if state == "near":
        return 22, f"documented {low:g}-{high:g}% O2 is close to {target}%", "measured"
    if dataset_max is not None and target > dataset_max and high >= dataset_max - 1e-9:
        return 22, (f"highest documented O2 in the dataset ({high:g}%), "
                    f"but the target {target}% is above anything tested"), "measured"
    distance = min(abs(target - low), abs(target - high))
    points = max(2, round(18 - distance / 2))
    return points, f"documented {low:g}-{high:g}% O2, {distance:.0f} points away from {target}%", "measured"


def pressure_points(phys, target):
    atm = (phys or {}).get("atmosphere") or {}
    low = atm.get("pressure_psia_min")
    high = atm.get("pressure_psia_max")
    if low is None or high is None:
        return 6, "no measured pressure", "unknown"
    state = covers(low, high, target)
    if state == "covers":
        return 25, f"documented {low:g}-{high:g} psia covers {target} psia", "measured"
    if state == "near":
        return 15, f"documented {low:g}-{high:g} psia is close to {target} psia", "measured"
    distance = min(abs(target - low), abs(target - high))
    points = max(2, round(13 - distance / 3))
    return points, f"documented {low:g}-{high:g} psia, {distance:.1f} psi away from {target}", "measured"


MATERIAL_WORDS = {
    "fabric": ("cotton", "nomex", "sibal", "fabric", "fiberglass", "cloth", "textile"),
    "plastic": ("pmma", "methyl methacrylate", "ultem", "silicone", "pyrell", "foam",
                "wax", "plastic", "polymer"),
    "liquid": ("heptane", "dodecane", "decane", "ethanol", "farnesane", "dibutyl",
               "dimethyl ether", "dme", "alkane"),
    "gas": ("methane", "ethylene", "propane", "propylene", "butane", "pentane",
            "hydrogen", "c2h4", "ch4", "n2", "nitrogen"),
}
GENERIC_MATERIALS = ("spacecraft materials", "materials", "various materials")


def classify_material(name):
    """Map a free-text material name to one of four hazard classes."""
    low = (name or "").lower()
    for cls, words in MATERIAL_WORDS.items():
        if any(w in low for w in words):
            return cls
    return None


def material_points(phys, env):
    """20 points = 12 for fuel state matching the environment
    + 8 for testing a material class that matters in that environment."""
    fuel = (phys or {}).get("fuel") or {}
    types = [t for t in (fuel.get("types") or []) if t not in ("unknown", "")]
    wanted = env["material"]

    if not types:
        state, why_state = 4, "fuel state not stated"
    elif wanted in types:
        state, why_state = 12, f"{wanted} fuel matches this environment"
    elif "mixed" in types:
        state, why_state = 8, "mixed fuel types"
    else:
        state, why_state = 2, f"fuel is {'/'.join(types)}, environment expects {wanted}"

    mats = [m for m in (fuel.get("materials") or []) if m]
    wanted_classes = env.get("material_class") or []
    by_class = {}
    for m in mats:
        cls = classify_material(m)
        if cls:
            by_class.setdefault(cls, []).append(m)

    if not mats:
        cls_pts, why_cls = 0, "no material named"
    elif any(c in wanted_classes for c in by_class):
        hit = next(c for c in by_class if c in wanted_classes)
        cls_pts, why_cls = 8, f"tested {hit} material ({', '.join(by_class[hit][:2])})"
    elif all(m.lower().strip() in GENERIC_MATERIALS for m in mats):
        cls_pts, why_cls = 4, "only a generic material category, no specific material"
    else:
        cls_pts, why_cls = 0, f"materials tested ({', '.join(mats[:2])}) fall outside this environment's class"

    source = "measured" if types else "unknown"
    return state + cls_pts, f"{why_state}; {why_cls}", source


def fire_points(rec):
    haystack = " ".join([
        rec.get("sub_area") or "",
        " ".join(rec.get("keywords") or []),
        rec.get("title") or "",
    ]).lower()
    hits = [w for w in FIRE_WORDS if w in haystack]
    if len(hits) >= 2:
        return 12, "explicit fire-safety framing", "measured"
    if hits:
        return 8, "partly fire-related", "measured"
    return 3, "combustion physics, not fire safety", "measured"


def platform_points(rec):
    platform = (rec.get("flight_platform") or "").strip().lower()
    if "iss" in platform or "space station" in platform:
        return 8, "flown on the ISS", "measured"
    # any crewed or uncrewed spacecraft is still a microgravity flight
    if any(k in platform for k in ("cygnus", "spacecraft", "shuttle", "soyuz", "dragon")):
        return 8, f"flown on {platform}", "measured"
    if platform in ("not applicable", "n/a", "none"):
        return 2, "not a flight experiment", "unknown"
    if platform:
        return 4, platform, "measured"
    return 2, "platform not stated", "unknown"


def coverage_points(phys):
    atm = (phys or {}).get("atmosphere") or {}
    flow = (phys or {}).get("flow") or {}
    fuel = (phys or {}).get("fuel") or {}
    fields = [
        atm.get("o2_percent_max") is not None,
        atm.get("pressure_psia_max") is not None,
        flow.get("velocity_cm_s_max") is not None,
        bool(fuel.get("materials")),
    ]
    return sum(25 for f in fields if f)


def main():
    investigations = json.load(open(os.path.join(DATA, "investigations.json"), encoding="utf-8"))
    physics = {r["id"]: r for r in json.load(open(os.path.join(DATA, "physics.json"), encoding="utf-8"))}
    findings_path = os.path.join(DATA, "findings.json")
    findings = json.load(open(findings_path, encoding="utf-8")) if os.path.exists(findings_path) else {}

    out = []
    for rec in investigations:
        phys = physics.get(rec["id"], {})
        scores = {}
        dataset_max_o2 = max(
            [(p.get("atmosphere") or {}).get("o2_percent_max") or 0 for p in physics.values()] + [0]
        )
        for env in ENVIRONMENTS:
            o2, o2_why, o2_src = oxygen_points(phys, env["o2"], dataset_max_o2)
            p, p_why, p_src = pressure_points(phys, env["pressure"])
            if (rec.get("experimental") or {}).get("kind") == "matrix":
                # a planned test matrix is not evidence that a condition was observed
                o2 = round(o2 * 0.75)
                p = round(p * 0.75)
                o2_why += " (planned test matrix, not per-test data)"
                p_why += " (planned test matrix, not per-test data)"
            m, m_why, m_src = material_points(phys, env)
            f, f_why, f_src = fire_points(rec)
            pl, pl_why, pl_src = platform_points(rec)
            total = o2 + p + m + f + pl
            scores[env["id"]] = {
                "score": total,
                "parts": [
                    {"label": "Oxygen fit", "points": o2, "max": 35, "why": o2_why, "source": o2_src},
                    {"label": "Pressure fit", "points": p, "max": 25, "why": p_why, "source": p_src},
                    {"label": "Material fit", "points": m, "max": 20, "why": m_why, "source": m_src},
                    {"label": "Fire-safety framing", "points": f, "max": 12, "why": f_why, "source": f_src},
                    {"label": "Flight platform", "points": pl, "max": 8, "why": pl_why, "source": pl_src},
                ],
            }

        exp = rec.get("experimental") or {}
        out.append({
            "id": rec["id"],
            "acronym": rec.get("acronym"),
            "title": rec["title"],
            "doi": rec.get("doi"),
            "sub_area": rec.get("sub_area"),
            "year": (rec.get("start_date") or "")[:4],
            "platform": rec.get("flight_platform"),
            "hardware": (rec.get("hardware") or {}).get("name"),
            "keywords": rec.get("keywords") or [],
            "objectives": (rec.get("objectives") or "")[:600],
            "publications": rec.get("publications") or {},
            "files": {"count": rec["files"]["count"], "size_gb": rec["files"]["size_gb"]},
            "experimental": {
                "rows": exp.get("rows"),
                "o2": exp.get("o2_pct"),
                "pressure": exp.get("pressure_psia"),
                "flow": exp.get("flow_cm_s"),
                "files": len(exp.get("files") or []),
            } if exp else None,
            "physics": {
                "fuel": (phys.get("fuel") or {}).get("types"),
                "materials": (phys.get("fuel") or {}).get("materials"),
                "o2": [phys.get("atmosphere", {}).get("o2_percent_min"),
                       phys.get("atmosphere", {}).get("o2_percent_max")],
                "pressure": [phys.get("atmosphere", {}).get("pressure_psia_min"),
                             phys.get("atmosphere", {}).get("pressure_psia_max")],
                "flow": [phys.get("flow", {}).get("velocity_cm_s_min"),
                         phys.get("flow", {}).get("velocity_cm_s_max")],
            },
            "findings": (findings.get(rec["id"]) if findings.get(rec["id"], {}).get("verified") else None),
            "findings_unverified": bool(findings.get(rec["id"]) and not findings[rec["id"]].get("verified")),
            "coverage": coverage_points(phys),
            "scores": scores,
            "source_url": rec["source_url"],
        })

    payload = {
        "environments": ENVIRONMENTS,
        "investigations": out,
        "meta": {
            "investigations": len(out),
            "with_experimental": sum(1 for r in out if r["experimental"]),
            "with_o2": sum(1 for r in out if r["physics"]["o2"][1] is not None or (r["experimental"] and r["experimental"]["o2"])),
            "with_pressure": sum(1 for r in out if r["physics"]["pressure"][1] is not None or (r["experimental"] and r["experimental"]["pressure"])),
            "with_findings": sum(1 for r in out if r["findings"]),
        },
    }

    path = os.path.join(DATA, "dashboard_data.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    print(f"wrote {path} ({os.path.getsize(path)/1024:.0f} KB)")

    for env in ENVIRONMENTS:
        top = sorted(out, key=lambda r: -r["scores"][env["id"]]["score"])[:5]
        print(f"\n{env['name']}:")
        for r in top:
            print(f"  {r['scores'][env['id']]['score']:3}  {r['id']:8} {str(r['acronym'])[:20]:20} {r['title'][:50]}")


if __name__ == "__main__":
    main()
