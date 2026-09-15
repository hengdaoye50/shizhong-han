"""精读类传：从儒林/党锢/文苑/独行/方术等原文中提取「侍中」句及传主。"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "raw" / "mirror" / "後漢書"
OUT = ROOT / "data" / "candidates" / "classbio_shizhong.csv"

# 类传文件
FILES = [
    "第七十四章-儒林列传上.txt",
    "第七十五章-儒林列传下.txt",
    "第六十一章-党锢列传.txt",
    "第七十六章-文苑列传上.txt",
    "第七十七章-文苑列传下.txt",
    "第七十八章-独行列传.txt",
    "第七十九章-方术列传上.txt",
    "第八十章-方术列传下.txt",
    "第七十一章-循吏列传.txt",
    "第七十二章-酷吏列传.txt",
    "第七十三章-宦者列传.txt",
    "第二十七章-张曹郑列传.txt",
    "第三十五章-班彪列传上.txt",
    "第三十六章-班彪列传下.txt",
]


def main() -> None:
    rows = []
    for name in FILES:
        # 找文件
        hits = list(BASE.rglob(name)) or list(BASE.rglob(f"*{name.split('-',1)[-1]}"))
        if not hits:
            # 宽松
            key = name.replace(".txt", "")
            hits = list(BASE.rglob(f"*{key[-8:]}*"))
        if not hits:
            print("missing", name)
            continue
        fp = hits[0]
        text = fp.read_text(encoding="utf-8", errors="ignore")
        # 章内分人：常见「○○字」或「○○，某地人」
        # 先按句切，记录最近本传主
        current = ""
        # 粗略：文件内每隔一段有「某某字」
        bio_pat = re.compile(r"(?:^|。|；)([一-龥]{2,3})(?:字[一-龥]{1,3}|，[一-龥]{0,6}人也)")
        bios = [(m.start(), m.group(1)) for m in bio_pat.finditer(text)]
        for sent in re.split(r"(?<=[。！？；])", text):
            if "侍中" not in sent:
                continue
            sent = sent.strip()
            if len(sent) < 8:
                continue
            # 找该句前最近 bio
            pos = text.find(sent[:20])
            owner = ""
            if pos >= 0 and bios:
                prior = [b for b in bios if b[0] <= pos]
                if prior:
                    owner = prior[-1][1]
            rows.append(
                {
                    "file": fp.name,
                    "hint_owner": owner,
                    "sentence": sent[:300],
                }
            )
        print(fp.name, "hits", sum(1 for r in rows if r["file"] == fp.name))

    print("total", len(rows))
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "hint_owner", "sentence"])
        w.writeheader()
        w.writerows(rows)
    print("->", OUT)


if __name__ == "__main__":
    main()
