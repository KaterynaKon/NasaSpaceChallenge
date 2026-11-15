#!/usr/bin/env python3
"""
Extract physical test parameters from NASA PSI investigation texts.

For every investigation we send the narrative fields (objectives, approach,
hypothesis, impacts, keywords) to an LLM with a strict JSON schema and ask for
fuel / atmosphere / flow / gravity / measurements, each backed by a verbatim
quote. A deterministic validator then rejects any number that does not appear
in the source text, so the dashboard never shows an invented value.

Inputs : data/investigations.json
Outputs: data/physics.json
         data/investigations.json  (records get a "physics" block)
"""

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

from openai import OpenAI

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
MODEL = os.getenv("PSI_LLM_MODEL", "gpt-4o-mini")

SCHEMA = {
    "type": "object",
    "properties": {
        "fuel": {
            "type": "object",
            "properties": {
                "types": {"type": "array", "items": {"type": "string",
                          "enum": ["solid", "liquid", "gaseous", "mixed", "unknown"]}},
                "materials": {"type": "array", "items": {"type": "string"}},
                "specimens": {"type": "array", "items": {"type": "string"}},
                "evidence": {"type": "string"},
            },
            "required": ["types", "materials", "specimens", "evidence"],
            "additionalProperties": False,
        },
        "atmosphere": {
            "type": "object",
            "properties": {
                "o2_percent_min": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                "o2_percent_max": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                "pressure_kpa": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                "diluents": {"type": "array", "items": {"type": "string"}},
                "evidence": {"type": "string"},
            },
            "required": ["o2_percent_min", "o2_percent_max", "pressure_kpa", "diluents", "evidence"],
            "additionalProperties": False,
        },
        "flow": {
            "type": "object",
            "properties": {
                "type": {"type": "string",
                         "enum": ["forced", "quiescent", "natural", "mixed", "unknown"]},
                "velocity_cm_s_min": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                "velocity_cm_s_max": {"anyOf": [{"type": "number"}, {"type": "null"}]},
                "evidence": {"type": "string"},
            },
            "required": ["type", "velocity_cm_s_min", "velocity_cm_s_max", "evidence"],
            "additionalProperties": False,
        },
        "gravity": {
            "type": "object",
            "properties": {
                "levels": {"type": "array", "items": {"type": "string",
                           "enum": ["microgravity", "partial", "normal", "unknown"]}},
                "evidence": {"type": "string"},
            },
            "required": ["levels", "evidence"],
            "additionalProperties": False,
        },
        "measurements": {"type": "array", "items": {"type": "string"}},
        "facility": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "notes": {"type": "string"},
    },
    "required": ["fuel", "atmosphere", "flow", "gravity", "measurements",
                 "facility", "confidence", "notes"],
    "additionalProperties": False,
}

SYSTEM = """You extract experimental parameters from NASA combustion-science
investigation descriptions. Rules:
- Use ONLY the supplied text. Never use outside knowledge.
- Every block must carry an "evidence" field: one sentence copied
  CHARACTER-FOR-CHARACTER from the supplied text, including its exact wording,
  punctuation and units. Do not paraphrase, shorten, translate or "clean up"
  the sentence. If no single sentence supports the values, copy the shortest
  contiguous phrase that does. If nothing supports a value, leave the numbers
  null, the arrays empty, and the evidence an empty string.
- Never convert or round units. Report numbers exactly as written in the text
  and in the unit the text uses; the schema's unit suffixes tell you what the
  field expects, so convert only when the text gives a different but explicitly
  convertible unit, and mention it in notes.
- "o2_percent_min/max" are percentages of oxygen (0-100), not fractions.
- "pressure_kpa" is absolute pressure in kPa.
- "velocity_cm_s_min/max" is flow speed in cm/s.
- "specimens" are physical sample shapes: rod, slab, cylinder, droplet, sphere,
  fabric sheet, etc.
- If the investigation is ground-based or modelling-only, gravity levels should
  say "normal" or "unknown" accordingly.
- confidence: high only when the text states the key parameters explicitly."""


def build_prompt(rec):
    parts = [
        f"ACCESSION: {rec['id']}",
        f"ACRONYM: {rec.get('acronym') or '(none)'}",
        f"TITLE: {rec['title']}",
        f"KEYWORDS: {', '.join(rec.get('keywords') or []) or '(none)'}",
        f"FLIGHT PLATFORM: {rec.get('flight_platform') or '(none)'}",
        f"HARDWARE: {(rec.get('hardware') or {}).get('name') or '(none)'}",
        "",
        "OBJECTIVES:",
        rec.get("objectives") or "(none)",
        "",
        "APPROACH:",
        rec.get("approach") or "(none)",
        "",
        "HYPOTHESIS:",
        rec.get("hypothesis") or "(none)",
        "",
        "IMPACTS:",
        rec.get("impacts") or "(none)",
    ]
    return "\n".join(parts)


def numbers_in(text):
    """All numeric tokens in the text, as floats, for the validator."""
    found = set()
    for tok in re.findall(r"\d+(?:[.,]\d+)?", text):
        try:
            found.add(float(tok.replace(",", ".")))
        except ValueError:
            pass
    return found


def norm(text):
    text = (text or "")
    for bad, good in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                      ("–", "-"), ("—", "-"), ("−", "-"), ("\u00a0", " ")):
        text = text.replace(bad, good)
    return re.sub(r"\s+", " ", text).strip().lower()


def norm_with_map(text):
    """Normalized text plus a map from each normalized char to its original index."""
    text = (text or "")
    for bad, good in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                      ("–", "-"), ("—", "-"), ("−", "-"), ("\u00a0", " ")):
        text = text.replace(bad, good)
    out_chars, index_map = [], []
    prev_space = True
    for i, ch in enumerate(text):
        if ch.isspace():
            if prev_space:
                continue
            out_chars.append(" ")
            index_map.append(i)
            prev_space = True
        else:
            out_chars.append(ch.lower())
            index_map.append(i)
            prev_space = False
    # trim trailing space
    while out_chars and out_chars[-1] == " ":
        out_chars.pop()
        index_map.pop()
    return "".join(out_chars), index_map


def slice_original(original, index_map, start, length):
    begin = index_map[start]
    end = index_map[start + length - 1] + 1
    return original[begin:end]


def quote_supported(quote, source_norm, original=None, index_map=None):
    """True if the quote (or a long run of its words) really occurs in the text.

    Models often paraphrase or trim quotes, so we accept the longest verbatim
    window of at least 8 words and return that exact snippet, in the original
    casing and punctuation when the index map is supplied.
    """
    q = norm(quote)
    if not q:
        return None
    if q in source_norm:
        pos = source_norm.index(q)
        if original is not None and index_map is not None:
            return slice_original(original, index_map, pos, len(q))
        return q
    words = q.split()
    for size in (14, 12, 10, 8):
        if len(words) < size:
            continue
        for start in range(len(words) - size + 1):
            window = " ".join(words[start:start + size])
            pos = source_norm.find(window)
            if pos != -1:
                if original is not None and index_map is not None:
                    return slice_original(original, index_map, pos, len(window))
                return window
    return None


def validate(result, source_text):
    """Drop numbers that are not literally present in the source text."""
    problems = []
    nums = numbers_in(source_text)

    def check(value, label):
        if value is None:
            return None
        if float(value) in nums:
            return value
        problems.append(f"{label}={value} not found in text")
        return None

    atm = result["atmosphere"]
    atm["o2_percent_min"] = check(atm["o2_percent_min"], "o2_percent_min")
    atm["o2_percent_max"] = check(atm["o2_percent_max"], "o2_percent_max")
    atm["pressure_kpa"] = check(atm["pressure_kpa"], "pressure_kpa")

    flow = result["flow"]
    flow["velocity_cm_s_min"] = check(flow["velocity_cm_s_min"], "velocity_cm_s_min")
    flow["velocity_cm_s_max"] = check(flow["velocity_cm_s_max"], "velocity_cm_s_max")

    # evidence must be a real substring of the supplied text
    src, src_map = norm_with_map(source_text)
    for block in ("fuel", "atmosphere", "flow", "gravity"):
        raw_ev = result[block].get("evidence") or ""
        if not norm(raw_ev):
            continue
        matched = quote_supported(raw_ev, src, source_text, src_map)
        if matched:
            result[block]["evidence"] = matched
        else:
            problems.append(f"{block}.evidence is not verbatim")
            result[block]["evidence"] = ""
            result["confidence"] = "low"

    if problems:
        result["validation_warnings"] = problems
    return result


def run_one(client, rec):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": build_prompt(rec)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "physics", "strict": True, "schema": SCHEMA},
        },
        max_completion_tokens=4000,
        extra_body={"reasoning": {"effort": "medium"}},
    )
    data = json.loads(resp.choices[0].message.content)
    return validate(data, build_prompt(rec))


def main():
    client = OpenAI()
    path = os.path.join(DATA, "investigations.json")
    records = json.load(open(path, encoding="utf-8"))

    def work(rec):
        try:
            physics = run_one(client, rec)
            status = "ok"
        except Exception as exc:                     # noqa: BLE001
            physics = {"error": str(exc)}
            status = "error"
        print(f"{rec['id']:8} {status:5} "
              f"fuel={','.join(physics.get('fuel', {}).get('types', [])) or '-':10} "
              f"o2={physics.get('atmosphere', {}).get('o2_percent_max')} "
              f"flow={physics.get('flow', {}).get('velocity_cm_s_max')}",
              flush=True)
        return rec, physics

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(work, records))

    out = []
    for rec, physics in results:
        rec["physics"] = physics
        out.append({"id": rec["id"], "acronym": rec.get("acronym"),
                    "title": rec["title"], **physics})

    json.dump(out, open(os.path.join(DATA, "physics.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(records, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    errors = [o for o in out if "error" in o]
    print(f"\nrecords: {len(out)}  errors: {len(errors)}")
    if errors:
        for e in errors:
            print("  ", e["id"], e["error"][:120])
        sys.exit(1)


if __name__ == "__main__":
    main()
