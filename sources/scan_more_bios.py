"""扫宦者/外戚/皇后及西汉儒林佞幸等，提侍中句+上下文定人。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS = [
    # 后汉 mirror
    ROOT / "data/raw/mirror/後漢書/第七十三章-宦者列传.txt",
    ROOT / "data/raw/mirror/後漢書/第十章-皇后纪上.txt",
    ROOT / "data/raw/mirror/後漢書/第十一章-皇后纪上.txt",
    ROOT / "data/raw/mirror/後漢書/第十二章-皇后纪下.txt",
    ROOT / "data/raw/mirror/漢書/传/第七十二章-王贡两龚鲍传.txt",
    ROOT / "data/raw/mirror/漢書/传/第九十三章-佞幸传.txt",
    ROOT / "data/raw/mirror/漢書/传/第八十八章-儒林传.txt",
    ROOT / "data/raw/mirror/漢書/传/第六十五章-东方朔传.txt",
    ROOT / "data/raw/mirror/漢書/传/第六十八章-霍光金日磾传.txt",
    ROOT / "data/raw/mirror/漢書/传/第五十九章-张汤传.txt",
    ROOT / "data/raw/mirror/漢書/传/第五十四章-王商史丹傅喜传.txt",
    ROOT / "data/raw/mirror/漢書/传/第八十二章-王商史丹傅喜传.txt",
]


def scan(fp: Path) -> None:
    if not fp.exists():
        # 宽松找
        key = fp.stem[-12:]
        hits = list(fp.parents[2].rglob(f"*{key}*")) if len(fp.parents) > 2 else []
        if hits:
            fp = hits[0]
        else:
            print("MISSING", fp.name)
            return
    text = fp.read_text(encoding="utf-8", errors="ignore")
    if "侍中" not in text:
        print("no 侍中", fp.name)
        return
    print("\n====", fp.name, "====")
    for sent in re.split(r"(?<=[。！？；])", text):
        if "侍中" not in sent:
            continue
        sent = sent.strip()
        if len(sent) < 8:
            continue
        idx = text.find(sent[:24])
        ctx = text[max(0, idx - 250) : idx].replace("\n", " ") if idx >= 0 else ""
        m = list(re.finditer(r"([一-龥]{2,3})字[一-龥]{1,3}", ctx))
        owner = m[-1].group(1) if m else "?"
        print(f"OWNER={owner} | {sent[:100]}")


def main() -> None:
    # 再动态补找 后汉皇后/宦者、汉书相关
    extra = []
    for pat in ["*宦者*", "*皇后纪*", "*佞幸*", "*儒林传*", "*霍光金日*", "*张汤*", "*王商史丹*"]:
        extra += list((ROOT / "data/raw/mirror").rglob(pat))
    files = TARGETS + extra
    seen = set()
    for fp in files:
        if fp in seen:
            continue
        seen.add(fp)
        scan(fp)


if __name__ == "__main__":
    main()
