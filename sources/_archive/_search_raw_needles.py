from pathlib import Path
import sys
sys.path.insert(0, r"D:\CODEX\两汉侍中数据库搭建\sources")
from hans import t2s
import re

RAW = Path(r"D:\CODEX\两汉侍中数据库搭建\data\raw")
needles = ["王莽秉政", "侍中復入", "侍中复入", "孔安國", "孔安国", "唾壺", "唾壶",
           "元兄", "秩千石", "秩千", "哀、平", "哀平", "負璽", "負玺", "僕射，後改",
           "侍中，秩", "金蟬左貂", "本秦丞相史"]
for n in needles:
    hits = []
    for p in RAW.rglob("*.txt"):
        try:
            t = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if n in t:
            i = t.find(n)
            frag = t[max(0, i-30):i+80].replace("\n", " ")
            hits.append((str(p.relative_to(RAW))[:50], frag[:90]))
            if len(hits) >= 2:
                break
    print(f"== {n} t2s={t2s(n)!r} hits={len(hits)}")
    for h in hits:
        print("  ", h[0], "|", h[1])

print("\n璽 in table?", "璽" in open(r"D:\CODEX\两汉侍中数据库搭建\sources\hans.py", encoding="utf-8").read())
print("t2s test:", t2s("行則負璽，秩千石，孔安國為侍中"))
