#!/usr/bin/env python3
"""
Download every Experimental table for the 24 combustion investigations
through the documented NASA PSI API.

Endpoints (see the PSI API guide):
  GET /geode-py/ws/api/investigations/files/search/{IDS}?page=&size=
  GET /geode-py/ws/api/investigations/PSI-{ID}/download?source=datamanager&file=

Input  : data/investigations.json  (the 24 PSI accession ids)
Output : incoming/api/<original file name>
         data/api_tables.json      (what was found and downloaded)

Why this exists: the tables were previously collected by hand. The public API
returns the same files, so the pipeline can refresh itself without a human.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "incoming", "api")
BASE = "https://psi.nasa.gov"
UA = {"User-Agent": "Mozilla/5.0 (compatible; FlameInFreefall/1.0)"}


def get_json(url, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as fh:
                return json.loads(fh.read().decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    return None


def list_files(acc_id):
    """Return every file entry for one investigation.

    The endpoint ignores `page` when it is 0 and returns an empty study map,
    but without paging parameters it returns the full list in one response.
    """
    url = f"{BASE}/geode-py/ws/api/investigations/files/search/{acc_id}"
    payload = get_json(url)
    study = (payload.get("studies") or {}).get(f"PSI-{acc_id}") or {}
    return study.get("study_files") or []


def is_table(name):
    low = name.lower()
    return "experimental" in low and low.endswith((".csv", ".xlsx", ".xls"))


def download(acc_id, name, dest):
    quoted = urllib.parse.quote_plus(name)
    url = f"{BASE}/geode-py/ws/api/investigations/PSI-{acc_id}/download?source=datamanager&file={quoted}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as fh:
        blob = fh.read()
    with open(dest, "wb") as out:
        out.write(blob)
    return len(blob)


def safe(name):
    return re.sub(r"[^\w.\- ]+", "_", name).strip()


def main():
    inv = json.load(open(os.path.join(DATA, "investigations.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    manifest, downloaded = [], 0

    for rec in sorted(inv, key=lambda r: int(r["id"].split("-")[1])):
        acc = int(rec["id"].split("-")[1])
        try:
            files = list_files(acc)
        except Exception as exc:  # noqa: BLE001
            print(f"{rec['id']}: file search failed ({exc})")
            manifest.append({"id": rec["id"], "error": str(exc), "tables": []})
            continue

        tables = [f for f in files if is_table(f.get("file_name", ""))]
        entry = {"id": rec["id"], "acronym": rec.get("acronym"),
                 "file_count": len(files), "tables": []}

        for f in tables:
            name = f["file_name"]
            dest = os.path.join(OUT, f"{rec['id']}__{safe(name)}")
            entry["tables"].append({"name": name, "size": f.get("file_size"),
                                    "restricted": f.get("restricted"), "path": dest})
            if f.get("restricted") or os.path.exists(dest):
                continue
            try:
                written = download(acc, name, dest)
                downloaded += 1
                print(f"{rec['id']}: {name} ({written/1024:.0f} KB)")
            except Exception as exc:  # noqa: BLE001
                entry["tables"][-1]["error"] = str(exc)
                print(f"{rec['id']}: {name} download failed ({exc})")

        manifest.append(entry)

    path = os.path.join(DATA, "api_tables.json")
    json.dump(manifest, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    with_tables = sum(1 for m in manifest if m.get("tables"))
    print(f"\n{with_tables} investigations expose an experimental table, "
          f"{downloaded} files downloaded to incoming/api")


if __name__ == "__main__":
    main()
