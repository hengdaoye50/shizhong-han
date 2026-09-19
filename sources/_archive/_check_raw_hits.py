from pathlib import Path
import re
RAW = Path(r"D:\CODEX\两汉侍中数据库搭建\data\raw")
for p in [
    RAW/"汉官六种/汉官六种_KR2l0023.txt",
    RAW/"职官分纪/殆知阁_职官分纪.txt",
    RAW/"汉制考/殆知阁_汉制攷.txt",
    RAW/"历代职官表/殆知阁_钦定历代职官表.txt",
    RAW/"北堂书钞/殆知阁_北堂书钞.txt",
    RAW/"汉官旧仪/殆知阁_汉官旧仪.txt",
    RAW/"东汉会要/殆知阁_东汉会要.txt",
]:
    t = p.read_text(encoding="utf-8", errors="ignore")
    print(p.name, "len", len(t), "侍中", t.count("侍中"), "sample_head", repr(t[:120]))
    # find first 侍中
    i = t.find("侍中")
    if i>=0:
        print("  ctx:", repr(t[max(0,i-40):i+60]))
    else:
        # try traditional variants?
        for ch in ["侍中", "侍中"]:
            pass
        print("  no 侍中; 中 count", t.count("中"), "侍 count", t.count("侍"))
