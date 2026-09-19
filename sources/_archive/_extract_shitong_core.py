"""从新拉取的十通/唐六典文本中抽出两汉侍中制度句。"""
from pathlib import Path
import re
import sys
sys.path.insert(0, r"D:\CODEX\两汉侍中数据库搭建\sources")
from hans import t2s
from build_institution_json import clean_quote, split_sentences

RAW = Path(r"D:\CODEX\两汉侍中数据库搭建\data\raw")
files = [
    RAW / "通典" / "通典_卷021.txt",
    RAW / "通典" / "通典_卷019.txt",
    RAW / "通典" / "通典_卷027.txt",
    RAW / "文献通考" / "文獻通考 (四庫全書本)_卷050.txt",
    RAW / "文献通考" / "文獻通考 (四庫全書本)_卷051.txt",
    RAW / "文献通考" / "文獻通考_卷五十七.txt",
    RAW / "文献通考" / "文獻通考_卷六十六.txt",
    RAW / "唐六典" / "唐六典_卷08.txt",
]
for f in files:
    if not f.exists():
        print("MISSING", f.name)
        continue
    print("\n########", f.name)
    text = f.read_text(encoding="utf-8", errors="ignore")
    # 关键词窗口
    keys = ["侍中", "門下", "门下", "少府", "加官", "禁中", "漢", "汉"]
    flat = clean_quote(text) or t2s(re.sub(r"\s+", "", text))
    # better: full clean then split
    sents = split_sentences(text)
    shown = 0
    for s in sents:
        if "侍中" not in s:
            continue
        # 偏好汉制/制度描述
        if not any(k in s for k in ["汉", "漢", "秦", "少府", "加官", "禁中", "门下", "門下", "秩", "员", "員", "貂", "玺", "璽", "周官", "丞相"]):
            continue
        if len(s) < 12:
            continue
        print("-", s[:160])
        shown += 1
        if shown >= 18:
            print("...")
            break
    print(f"(shown {shown} / total 侍中 sents {sum(1 for s in sents if '侍中' in s)})")
