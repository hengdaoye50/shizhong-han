"""过滤 wide mined：只保留证据句可确认任侍中者。"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDE = ROOT / "data" / "candidates" / "persons_context_wide.csv"
OUT_OK = ROOT / "data" / "candidates" / "persons_wide_ok.csv"
OUT_NO = ROOT / "data" / "candidates" / "persons_wide_reject.csv"

# 证据句必须含：人名 + 侍中（或 侍中 + 人名），且不是纯列名
# 或句中「X为侍中」「以X为侍中」「拜X侍中」

def confirms(person: str, sentence: str) -> str:
    """返回 Y / N / U"""
    s = (sentence or "").replace(" ", "")
    p = person
    # 直接相邻
    if f"{p}为侍中" in s or f"{p}為侍中" in s:
        return "Y"
    if f"{p}拜侍中" in s or f"拜{p}侍中" in s:
        return "Y"
    if f"{p}稍迁侍中" in s or f"{p}稍遷侍中" in s or f"{p}迁侍中" in s or f"{p}遷侍中" in s:
        return "Y"
    if f"{p}复为侍中" in s or f"{p}復為侍中" in s or f"{p}再迁侍中" in s or f"{p}再遷侍中" in s:
        return "Y"
    if f"以{p}为侍中" in s or f"以{p}為侍中" in s:
        return "Y"
    if f"侍中{p}" in s:
        # 「侍中某」——多数是任职
        return "Y"
    if f"{p}侍中" in s:
        # 「与侍中某」
        return "Y"
    # 「某，为侍中」
    if re.search(rf"{p}[，,]为侍中", s):
        return "Y"
    # 「征拜侍中」无名——U
    if "侍中" in s and p in s:
        return "U"
    return "N"


# 明确误检
DROP = {
    "郭皇后", "阴曹曾", "张者", "元常", "王山", "王考", "王满", "王滿",
    "刘寬", "周澤", "董賢", "朱買臣", "陈羣", "阴識", "张興", "赵彥",
    "金日磾", "傅俊", "桓榮", "施雠", "梁丘贺", "石显",  # 已有/非新
}

RENAME = {
    "刘寬": "刘宽",
    "周澤": "周泽",
    "董賢": "董贤",
    "朱買臣": "朱买臣",
    "陈羣": "陈群",
    "阴識": "阴识",
    "张興": "张兴",
    "赵彥": "赵彦",
    "桓榮": "桓荣",
}


def main() -> None:
    rows = list(csv.DictReader(WIDE.open(encoding="utf-8-sig")))
    ok = defaultdict(list)
    no = []
    for r in rows:
        person = RENAME.get(r["person"], r["person"])
        if person in DROP or len(person) < 2:
            no.append({**r, "reason": "drop/rename"})
            continue
        flag = confirms(person, r.get("sentence") or "")
        if flag == "Y":
            r = dict(r)
            r["person"] = person
            ok[person].append(r)
        elif flag == "U":
            no.append({**r, "reason": "uncertain", "person_new": person})
        else:
            no.append({**r, "reason": "not_confirmed", "person_new": person})

    print("confirmed persons", len(ok), "ev", sum(len(v) for v in ok.values()))
    for p, evs in sorted(ok.items(), key=lambda x: -len(x[1])):
        print(f"  {len(evs):2d} {p} | {evs[0]['sentence'][:70]}")
    with OUT_OK.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for p, evs in ok.items():
            for e in evs:
                w.writerow(e)
    with OUT_NO.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["person", "sentence", "reason", "book"], extrasaction="ignore")
        w.writeheader()
        for r in no:
            w.writerow(r)
    print("rejected", len(no), "->", OUT_NO)


if __name__ == "__main__":
    main()
