"""第二轮：从「未解析」候选句中再挖侍中人名，合并进 evidence。

针对漏掉的句式：以X为侍中、徵X为侍中、X入为侍中、擢为侍中（前文有名）、
侍中守尚书令、加侍中 等。
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "data" / "candidates" / "shizhong_candidates.csv"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"

SURNAMES = (
    "霍|金|上官|桑|杨|楊|张|張|王|李|赵|趙|陈|陳|刘|劉|邓|鄧|耿|窦|竇|马|馬|班|梁|袁|曹|"
    "孙|孫|周|吴|吳|郑|鄭|朱|许|許|冯|馮|董|萧|蕭|程|傅|贾|賈|夏侯|诸葛|諸葛|司马|司馬|"
    "皇甫|鲁|魯|尹|何|郭|阴|陰|来|來|岑|任|宋|杜|桓|虞|黄|黃|蔡|荀|孔|钟|鍾|华|華|卫|衛|"
    "陆|陸|顾|顧|纪|紀|徐|谢|謝|韩|韓|唐|石|白|侯|段|汪|田|姚|毛|秦|江|史|黎|乔|喬|龚|龔|"
    "于|於|齐|齊|康|伍|余|元|刁|单|單|施|丁|贺|贺|郗|习|習|滕|是|濮|步|阙|闕"
)

NAME = rf"((?:{SURNAMES})[一-龥]{{1,2}})"

PATTERNS = [
    # 以/拜/徵 + X + 为/為/拜 + 侍中
    re.compile(rf"(?:以|拜|徵|征|举|薦|荐|引|表|迁|遷|擢|复|復|再|入|出)[一-龥]{{0,6}}{NAME}(?:为|為|拜|遷|迁)?侍中"),
    # X 入/复/再/稍迁 为 侍中
    re.compile(rf"{NAME}(?:入|復|再|稍遷|稍迁|遷|迁|拜|徵|征)(?:为|為)侍中"),
    # 徵 X 为侍中
    re.compile(rf"(?:徵|征|召|辟|薦|荐|举|引)侍中?{NAME}"),
    # 侍中 X 守/领
    re.compile(rf"侍中{NAME}(?:守|領|领)"),
    # 侍中、侍郎 X
    re.compile(rf"侍中[、，]侍郎{NAME}"),
    # 尚书/将军 + X + 加侍中 / 为侍中
    re.compile(rf"{NAME}(?:加|為|为)侍中"),
    # 先主/帝 以 X 为侍中
    re.compile(rf"以{NAME}(?:为|為)侍中"),
]

T2S = {
    "劉": "刘", "張": "张", "楊": "杨", "趙": "赵", "陳": "陈", "鄧": "邓",
    "竇": "窦", "馬": "马", "孫": "孙", "鄭": "郑", "許": "许", "馮": "冯",
    "蕭": "萧", "賈": "贾", "諸": "诸", "諸葛": "诸葛", "魯": "鲁",
    "陰": "阴", "來": "来", "黃": "黄", "鍾": "钟", "華": "华", "衛": "卫",
    "陸": "陆", "顧": "顾", "紀": "纪", "韓": "韩", "謝": "谢", "龔": "龚",
    "喬": "乔", "齊": "齐", "單": "单", "習": "习", "闕": "阙",
}

DENY = {
    "尚书", "将军", "校尉", "太守", "刺史", "光禄", "大夫", "中郎", "仆射",
    "于是", "即位", "侍中", "黄门", "长史", "参军", "东西", "左右", "中外",
}


def norm(n: str) -> str:
    for a, b in T2S.items():
        n = n.replace(a, b)
    # 去尾
    for suf in ("为", "為", "拜", "加", "等", "曰", "书", "書", "奏", "言", "上", "下", "入", "出"):
        if len(n) > 2 and n.endswith(suf):
            n = n[: -len(suf)]
    return n


def extract(s: str) -> list[str]:
    s = s.replace(" ", "").replace("\n", "")
    out = []
    for pat in PATTERNS:
        for m in pat.finditer(s):
            g = m.group(1)
            name = norm(g)
            if 2 <= len(name) <= 4 and name not in DENY:
                if any(name.endswith(x) for x in ("尉", "大夫", "将军", "校尉", "尚书")):
                    continue
                out.append(name)
    # unique
    res, seen = [], set()
    for n in out:
        if n not in seen:
            seen.add(n)
            res.append(n)
    return res


def main() -> None:
    rows = list(csv.DictReader(CAND.open(encoding="utf-8-sig")))
    ev = list(csv.DictReader(EV.open(encoding="utf-8-sig")))
    parsed = {int(r["cand_row"]) for r in ev if str(r.get("cand_row", "")).isdigit()}

    # 已有规范名
    known = {r["person"] for r in ev}

    new_bucket = defaultdict(list)
    still = 0
    for i, r in enumerate(rows, start=2):
        if i in parsed:
            continue
        names = extract(r.get("sentence") or "")
        if not names:
            still += 1
            continue
        for n in names:
            new_bucket[n].append(
                {
                    "person": n,
                    "cand_row": i,
                    "book": r.get("book"),
                    "juan": r.get("juan"),
                    "sentence": r.get("sentence"),
                    "source_file": r.get("source_file"),
                    "alias_in_sentence": "",
                }
            )

    print("new persons", len(new_bucket), "new evidence", sum(len(v) for v in new_bucket.values()))
    print("still unparsed", still)
    # 与已有对比
    only_new = [p for p in new_bucket if p not in known]
    print("not in current evidence", len(only_new))
    print("sample new:", sorted(only_new, key=lambda p: -len(new_bucket[p]))[:40])

    # 追加 evidence（不覆盖旧文件，写 pass2）
    out = ROOT / "data" / "candidates" / "persons_evidence_pass2.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"],
        )
        w.writeheader()
        for p, evs in sorted(new_bucket.items(), key=lambda x: -len(x[1])):
            for e in evs:
                w.writerow(e)
    print("->", out)


if __name__ == "__main__":
    main()
