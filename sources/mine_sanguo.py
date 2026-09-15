"""从队列专挖三國志中明文任侍中者。"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "candidates" / "unparsed_namequeue.csv"
OUT = ROOT / "data" / "candidates" / "persons_sanguo_mined.csv"

SURNAMES = (
    "霍|金|杨|楊|张|張|王|李|赵|趙|陈|陳|刘|劉|邓|鄧|耿|窦|竇|马|馬|班|梁|袁|曹|"
    "孙|孫|周|吴|吳|郑|鄭|朱|许|許|冯|馮|董|萧|蕭|程|傅|贾|賈|夏侯|诸葛|諸葛|"
    "司马|司馬|皇甫|鲁|魯|尹|何|郭|阴|陰|来|來|岑|任|宋|杜|桓|虞|黄|黃|蔡|荀|"
    "孔|钟|鍾|华|華|卫|衛|陆|陸|顾|顧|纪|紀|徐|谢|謝|韩|韓|唐|石|白|侯|段|"
    "汪|田|姚|毛|秦|江|史|黎|乔|喬|龚|龔|于|於|齐|齊|康|伍|余|元|刁|单|單|施|"
    "丁|贺|郗|习|習|滕|是|步|灌|祭|铫|銚|濮|淳于|申屠|毋|兒|儿|奚|嵇|阮|向|"
    "钟会|鍾會|王沈|王業|王业|裴秀|桓階|桓阶|陳矯|陈矫|陳羣|陈群|董遇|卫臻|衞臻"
)

NAME = rf"((?:{SURNAMES})[一-龥]{{0,2}})"

PATS = [
    re.compile(rf"(?:为|為|拜|遷|迁|稍遷|稍迁|復為|复为|再為|再为|入為|入为|加)侍中[、，]?{NAME}"),
    re.compile(rf"{NAME}(?:为|為|拜|遷|迁|加)侍中"),
    re.compile(rf"侍中{NAME}"),
    re.compile(rf"呼侍中{NAME}"),
    re.compile(rf"使侍中{NAME}"),
    re.compile(rf"以{NAME}(?:为|為)侍中"),
]


def main() -> None:
    rows = list(csv.DictReader(QUEUE.open(encoding="utf-8-sig")))
    mined = defaultdict(list)
    for r in rows:
        if r["book"] != "三國志":
            continue
        s = (r.get("sentence") or "").replace(" ", "")
        found = []
        for pat in PATS:
            for m in pat.finditer(s):
                n = m.group(1).strip()
                if 2 <= len(n) <= 4:
                    found.append(n)
        # 去噪
        found = [n for n in found if n not in {"侍中", "尚书", "将军", "黄门", "于是"}]
        for n in found[:2]:
            mined[n].append(r)
    print("mined", len(mined))
    for p, evs in sorted(mined.items(), key=lambda x: -len(x[1]))[:40]:
        print(f"  {len(evs):2d} {p} | {evs[0]['sentence'][:80]}")
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"],
        )
        w.writeheader()
        for p, evs in mined.items():
            for e in evs:
                w.writerow(
                    {
                        "person": p,
                        "cand_row": e.get("cand_row"),
                        "book": e.get("book"),
                        "juan": e.get("juan"),
                        "sentence": e.get("sentence"),
                        "source_file": "",
                        "alias_in_sentence": "",
                    }
                )
    print("->", OUT)


if __name__ == "__main__":
    main()
