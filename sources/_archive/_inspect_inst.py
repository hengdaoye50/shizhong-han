from pathlib import Path
import json

p = Path(r"D:\CODEX\两汉侍中数据库搭建\shizhongdata\data\institution.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("sources_note:")
for s in d.get("sources_note") or []:
    print(" -", s)
print("\nstats", d.get("stats"))
print()
for ph in d["phases"]:
    print("====", ph["id"], ph["title"])
    for q in (ph.get("quotes") or [])[:6]:
        print(f"  [{q.get('kind')}] {q.get('book')} {q.get('juan')}")
        print("   ", q.get("sentence", "")[:140])
