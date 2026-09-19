import json
from pathlib import Path

d = json.loads(
    Path(r"D:\CODEX\两汉侍中数据库搭建\shizhongdata\data\institution.json").read_text(
        encoding="utf-8"
    )
)
for p in d["phases"]:
    qs = p.get("quotes") or []
    first = qs[0]["book"] if qs else "-"
    sent = (qs[0]["sentence"][:40] if qs else "")
    print(f"{p['id']:16s} quotes={len(qs):2d} curated={len(p.get('curated_points') or [])} first={first} {sent}")
print("gaps", len(d["roster_check"]["gaps"]))
print("notes", len(d["roster_check"]["notes"]))
dc = list(Path(r"D:\CODEX\两汉侍中数据库搭建\data\candidates\draft_cards").glob("*.md"))
print("drafts", [x.name for x in dc])
for n in ["獨斷", "漢官舊儀", "西漢會要", "東漢會要"]:
    p = Path(r"D:\CODEX\两汉侍中数据库搭建\data\raw") / n
    print(n, "files", len(list(p.glob("*.txt"))) if p.exists() else 0)
