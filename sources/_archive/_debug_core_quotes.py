from pathlib import Path
import sys
sys.path.insert(0, r"D:\CODEX\两汉侍中数据库搭建\sources")
from hans import t2s, norm_quote
import re
from build_institution_json import extract_from_file, clean_quote, is_core_candidate, book_key, juan_label, RAW, phase_of

# find specific key quotes
keys = [
    "明经者充侍中", "取明经", "负玺", "改为祭酒",
    "王莽秉政", "侍中复入", "更始立", "哀、平间", "哀平间",
    "元兄", "贾逵", "孔安国", "皆加官", "员各六人", "典制度",
    "属少府", "秩千石", "侍中寺",
]
found = {k: [] for k in keys}
for path in RAW.rglob("*.txt"):
    if path.suffix != ".txt":
        continue
    for q, book, juan, rel in extract_from_file(path):
        for k in keys:
            if k in q or k in t2s(q):
                found[k].append((book, juan, q[:100]))

for k, items in found.items():
    print(f"== {k} ({len(items)})")
    for it in items[:3]:
        print("  ", it)
