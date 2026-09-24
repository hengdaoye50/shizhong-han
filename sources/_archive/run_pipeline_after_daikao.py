# -*- coding: utf-8 -*-
"""待考审定后全量重跑流水线。"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\CODEX\两汉侍中数据库搭建")
PY = sys.executable
STEPS = [
    "sources/enrich_year_clues.py",
    "sources/fix_dup_quote_lines.py",
    "sources/build_bio_store.py",
    "sources/export_web_json.py",
    "sources/build_timeline.py",
    "sources/export_graph_json.py",
    "sources/upsert_cards_to_db.py",
]

env = {"PYTHONIOENCODING": "utf-8"}
for s in STEPS:
    p = ROOT / s
    if not p.exists():
        print("MISSING", s)
        continue
    print("=" * 50)
    print("RUN", s)
    r = subprocess.run([PY, str(p)], cwd=str(ROOT), env={**__import__("os").environ, **env},
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-2000:] if r.stdout else "")
    if r.stderr:
        print("STDERR:", r.stderr[-1500:])
    print("RC", r.returncode)
print("PIPELINE DONE")
