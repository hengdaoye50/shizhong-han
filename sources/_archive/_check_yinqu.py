import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
c = sqlite3.connect(ROOT / "data" / "db" / "shizhong.db")
rows = c.execute(
    "SELECT from_name, to_name, rel_type FROM relation WHERE from_name LIKE ? OR to_name LIKE ? OR from_name LIKE ? OR to_name LIKE ?",
    ("%璩%", "%璩%", "%应璩%", "%应璩%"),
).fetchall()
print("rels", rows)
print("persons", c.execute("SELECT id, name FROM person WHERE name LIKE '%璩%'").fetchall())
t = json.loads((ROOT / "shizhongdata" / "data" / "timeline.json").read_text(encoding="utf-8"))
print("meta", t["meta"]["plotted"], t["meta"]["count"])
for it in t["items"]:
    if "璩" in (it.get("name") or ""):
        print("plot", it["name"], it.get("precision"), it.get("dynasty"), it.get("nature", "")[:40])
for a in t["aggregates"]:
    if any("璩" in n for n in a.get("names") or []):
        print("agg", a["dynasty"], [n for n in a["names"] if "璩" in n])
