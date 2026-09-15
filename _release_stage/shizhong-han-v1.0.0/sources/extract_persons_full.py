"""从全量候选句抽取侍中人名，归并繁简，输出 persons 与 evidence。

用法:
  python sources/extract_persons_full.py
  python sources/extract_persons_full.py --min-evidence 1
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "data" / "candidates" / "shizhong_candidates.csv"
OUT_DIR = ROOT / "data" / "candidates"

# 常见姓（| 分隔，繁简并列）
SURNAMES = (
    "霍|金|上官|桑|杨|楊|张|張|王|李|赵|趙|陈|陳|刘|劉|邓|鄧|耿|窦|竇|马|馬|班|梁|袁|曹|"
    "孙|孫|周|吴|吳|郑|鄭|朱|许|許|冯|馮|董|萧|蕭|程|傅|贾|賈|夏侯|诸葛|諸葛|司马|司馬|"
    "皇甫|鲁|魯|尹|何|郭|阴|陰|来|來|岑|銚|铫|祭|任|蓋|盖|宋|杜|桓|虞|黄|黃|蔡|荀|孔|"
    "钟|鍾|华|華|郗|卫|衛|陆|陸|顾|顧|纪|紀|第五|东方|東方|毋|灌|卜|兒|儿|奚|嵇|阮|向|"
    "申屠|公孙|公孫|歐|欧|嚴|严|徐|谢|謝|韓|韩|唐|冯|石|白|侯|段|邵|汪|田|姚|毛|秦|"
    "江|史|黎|乔|喬|龚|龔|于|於|傅|齐|齊|康|伍|余|元|顧|顾"
)

# 繁→简常用字（人名相关，够试点/全量骨架用；非完整 OpenCC）
T2S = str.maketrans(
    {
        "劉": "刘", "張": "张", "楊": "杨", "趙": "赵", "陳": "陈", "鄧": "邓",
        "竇": "窦", "馬": "马", "孫": "孙", "鄭": "郑", "許": "许", "馮": "冯",
        "蕭": "萧", "賈": "贾", "諸": "诸", "葛": "葛", "司": "司", "魯": "鲁",
        "陰": "阴", "來": "来", "蓋": "盖", "黃": "黄", "鍾": "钟", "華": "华",
        "衛": "卫", "陸": "陆", "顧": "顾", "紀": "纪", "竇": "窦", "歐": "欧",
        "陽": "阳", "陽": "阳", "賞": "赏", "欽": "钦", "湯": "汤", "敞": "敞",
        "涉": "涉", "憲": "宪", "篤": "笃", "騭": "骘", "勳": "勋", "駰": "骃",
        "瑒": "玚", "暢": "畅", "薦": "荐", "車": "车", "騎": "骑", "將": "将",
        "軍": "军", "遷": "迁", "為": "为", "徵": "征", "謁": "谒", "僕": "仆",
        "射": "射", "祿": "禄", "衛": "卫", "光": "光", "祿": "禄", "大": "大",
        "夫": "夫", "都": "都", "尉": "尉", "奉": "奉", "駙": "驸", "日": "日",
        "磾": "磾", "莽": "莽", "何": "何", "羅": "罗", "史": "史", "高": "高",
        "瑜": "瑜", "董": "董", "扶": "扶", "郭": "郭", "舉": "举", "耿": "耿",
        "良": "良", "逵": "逵", "賈": "贾", "伍": "伍", "孚": "孚", "建": "建",
        "安": "安", "上": "上", "金": "金",
    }
)


def norm_name(s: str | None) -> str:
    if not s:
        return ""
    return s.translate(T2S).strip()


# 官名/虚词黑名单（归一后）
DENY = {
    "祭酒", "卫尉", "马都尉", "驸马都尉", "奉车都尉", "光禄大夫", "中郎将",
    "仆射", "尚书", "尚书令", "御史", "御史大夫", "史大夫", "史中丞",
    "于是", "即位", "王即位", "大将军", "车骑将军", "骠骑将军", "将军",
    "校尉", "太守", "刺史", "县令", "博士", "议郎", "郎中", "给事中",
    "散骑", "谏大夫", "光禄勋", "执金吾", "少府", "太仆", "廷尉",
    "大鸿胪", "大司农", "宗正", "太常", "卫将军", "前将军", "后将军",
    "左将军", "右将军", "司空", "司徒", "太尉", "丞相", "尚书仆射",
    "侍中仆射", "黄门", "中常侍", "小黄门", "长乐", "未央", "建章",
    "出为", "入为", "复为", "再为", "稍迁", "迁为", "拜为", "征拜",
    "擢为", "加侍中", "为侍中", "谓侍中", "使侍中", "下侍中", "与侍中",
    "及侍中", "从侍中", "遣侍中", "引侍中", "表侍中", "举侍中",
}

# 姓 + 1~2 字名
NAME = rf"((?:{SURNAMES})[一-龥]{{1,2}})"

PATTERNS = [
    re.compile(rf"侍中(?:僕射|仆射)?[、，]?{NAME}"),
    re.compile(rf"{NAME}(?:字[一-龥]{{1,2}})?(?:稍遷|稍迁|遷|迁|為|为|拜|復為|复为|再為|再为|入為|入为|出為|出为)侍中"),
    re.compile(rf"[|｜]{NAME}為侍中"),
]


def clean_person_name(name: str) -> str:
    """去掉误吞的动词/虚词尾巴。"""
    for suf in (
        "出", "入", "为", "為", "荐", "薦", "慕", "欲", "等", "上", "下",
        "代", "安", "并", "並", "及", "与", "與", "以", "将", "將",
        "自", "乃", "遂", "因", "复", "復", "再", "更", "皆", "咸",
    ):
        if len(name) > 2 and name.endswith(suf):
            name = name[: -len(suf)]
    return name


def extract_from_sentence(s: str) -> list[str]:
    s = s.replace(" ", "").replace("\n", "")
    found: list[str] = []
    for pat in PATTERNS:
        for m in pat.finditer(s):
            g = m.group(1) if m.lastindex else None
            if not g:
                continue
            name = clean_person_name(norm_name(g))
            if not (2 <= len(name) <= 4):
                continue
            if name in DENY:
                continue
            if any(name.endswith(x) for x in ("尉", "大夫", "将军", "校尉", "太守", "尚书")):
                continue
            found.append(name)
    out, seen = [], set()
    for n in found:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-evidence", type=int, default=1)
    args = ap.parse_args()

    rows = list(csv.DictReader(CAND.open(encoding="utf-8-sig")))
    # person -> list of evidence dicts
    bucket: dict[str, list[dict]] = defaultdict(list)
    unparsed = 0
    for i, r in enumerate(rows, start=2):
        sent = r.get("sentence") or ""
        names = extract_from_sentence(sent)
        for n in names:
            bucket[n].append(
                {
                    "cand_row": i,
                    "book": r.get("book"),
                    "juan": r.get("juan"),
                    "sentence": sent[:300],
                    "source_file": r.get("source_file"),
                }
            )
        if not names:
            unparsed += 1

    # 写 persons_evidence.csv（一人多行）
    ev_path = OUT_DIR / "persons_evidence.csv"
    with ev_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["person", "cand_row", "book", "juan", "sentence", "source_file"]
        )
        w.writeheader()
        for person in sorted(bucket, key=lambda p: -len(bucket[p])):
            for ev in bucket[person]:
                w.writerow({"person": person, **ev})

    # 写 persons_index.csv
    idx_path = OUT_DIR / "persons_index.csv"
    kept = []
    for person, evs in sorted(bucket.items(), key=lambda x: -len(x[1])):
        if len(evs) < args.min_evidence:
            continue
        books = sorted({e["book"] for e in evs})
        kept.append(
            {
                "person": person,
                "n_evidence": len(evs),
                "books": "|".join(books),
                "sample": evs[0]["sentence"][:120],
            }
        )
    with idx_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["person", "n_evidence", "books", "sample"])
        w.writeheader()
        w.writerows(kept)

    print(f"candidates={len(rows)} persons={len(bucket)} kept>={args.min_evidence}:{len(kept)} unparsed={unparsed}")
    print(f"-> {idx_path}")
    print(f"-> {ev_path}")
    print("top30:")
    for row in kept[:30]:
        print(f"  {row['n_evidence']:3d}  {row['person']}  {row['books'][:40]}")


if __name__ == "__main__":
    main()
