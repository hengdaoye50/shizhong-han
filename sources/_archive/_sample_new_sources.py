"""抽样新入库非维基文献中的制度性「侍中」句。"""
from pathlib import Path
import re
import sys
sys.path.insert(0, r"D:\CODEX\两汉侍中数据库搭建\sources")
from build_institution_json import clean_quote, split_sentences

RAW = Path(r"D:\CODEX\两汉侍中数据库搭建\data\raw")
targets = [
    "汉官六种/汉官六种_KR2l0023.txt",
    "汉制考/殆知阁_汉制攷.txt",
    "职官分纪/殆知阁_职官分纪.txt",
    "历代职官表/殆知阁_钦定历代职官表.txt",
    "北堂书钞/殆知阁_北堂书钞.txt",
    "初学记/殆知阁_初学记.txt",
    "两汉诏令/殆知阁_两汉诏令.txt",
    "东汉会要/殆知阁_东汉会要.txt",
    "西汉会要/殆知阁_西汉会要.txt",
    "汉官旧仪/殆知阁_汉官旧仪.txt",
]
keys = ["加官", "少府", "禁中", "无员", "無員", "秩", "冠", "貂", "玺", "璽", "仆射", "僕射", "侍中寺", "门下", "門下", "秦", "周官", "丞相史", "明经", "負璽", "负玺", "省尚书", "漢官", "汉官"]
for rel in targets:
    p = RAW / rel
    if not p.exists():
        print("MISSING", rel)
        continue
    print("\n########", rel)
    text = p.read_text(encoding="utf-8", errors="ignore")
    sents = split_sentences(text)
    hits = []
    for s in sents:
        if "侍中" not in s or len(s) < 12:
            continue
        if any(k in s for k in keys):
            hits.append(s)
    # unique-ish
    seen = set()
    shown = 0
    for s in hits:
        fp = s[:24]
        if fp in seen:
            continue
        seen.add(fp)
        print("-", s[:150])
        shown += 1
        if shown >= 12:
            break
    print(f"(inst-like unique~{len(seen)} total_sents_with_侍中={sum(1 for s in sents if '侍中' in s)})")
