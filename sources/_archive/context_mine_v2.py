"""带 source_file 的上下文挖人：queue cand_row → 主表 source_file → 前后文定位主语。"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "candidates" / "unparsed_namequeue.csv"
MAIN = ROOT / "data" / "candidates" / "shizhong_candidates.csv"
OUT = ROOT / "data" / "candidates" / "persons_context_mined.csv"

SURNAMES = (
    "霍|金|上官|桑|杨|楊|张|張|王|李|赵|趙|陈|陳|刘|劉|邓|鄧|耿|窦|竇|马|馬|班|梁|袁|曹|"
    "孙|孫|周|吴|吳|郑|鄭|朱|许|許|冯|馮|董|萧|蕭|程|傅|贾|賈|夏侯|诸葛|諸葛|司马|司馬|"
    "皇甫|鲁|魯|尹|何|郭|阴|陰|来|來|岑|任|宋|杜|桓|虞|黄|黃|蔡|荀|孔|钟|鍾|华|華|卫|衛|"
    "陆|陸|顾|顧|纪|紀|徐|谢|謝|韩|韓|唐|石|白|侯|段|汪|田|姚|毛|秦|江|史|黎|乔|喬|龚|龔|"
    "于|於|齐|齊|康|伍|余|元|刁|单|單|施|丁|贺|郗|习|習|滕|是|步|灌|祭|铫|銚|濮"
)

BIO_OPEN = re.compile(
    rf"((?:{SURNAMES})[一-龥]{{1,2}})(?:字[一-龥]{{1,3}}|[，,．。][一-龥]{{0,8}}人也)"
)

T2S = str.maketrans({
    "劉": "刘", "張": "张", "楊": "杨", "趙": "赵", "陳": "陈", "鄧": "邓",
    "竇": "窦", "馬": "马", "孫": "孙", "鄭": "郑", "許": "许", "馮": "冯",
    "蕭": "萧", "賈": "贾", "魯": "鲁", "陰": "阴", "來": "来", "黃": "黄",
    "鍾": "钟", "華": "华", "衛": "卫", "陸": "陆", "顧": "顾", "紀": "纪",
    "韓": "韩", "謝": "谢", "龔": "龚", "喬": "乔", "齊": "齐", "單": "单",
    "習": "习", "闕": "阙",
})

DENY = {
    "侍中", "尚书", "将军", "黄门", "于是", "更始", "光武", "顺帝", "和帝",
    "安帝", "桓帝", "灵帝", "献帝", "肃宗", "显宗", "元帝", "成帝", "哀帝",
    "平帝", "武帝", "昭帝", "宣帝", "章帝", "明帝", "冲帝", "质帝", "少帝",
    "祭酒", "卫尉", "步兵", "元以", "任并", "博士", "议郎", "太守", "刺史",
}


def norm(n: str) -> str:
    return n.translate(T2S).strip()


def load_ctx(sf: str, sentence: str) -> str:
    p = ROOT / sf
    if not p.exists():
        return sentence
    text = p.read_text(encoding="utf-8", errors="ignore")
    frag = re.sub(r"[「」『』\[\]（）()0-9\s]", "", sentence)[:14]
    idx = text.find(frag)
    if idx < 0:
        frag = frag[:8]
        idx = text.find(frag)
    if idx < 0:
        return sentence
    return text[max(0, idx - 500) : idx + 250]


def guess(ctx: str, sentence: str) -> str | None:
    s = sentence.replace(" ", "")
    # 句内
    m = re.search(rf"((?:{SURNAMES})[一-龥]{{1,2}})(?:为|為|拜|遷|迁|稍遷|稍迁|復為|复为)侍中", s)
    if m:
        return norm(m.group(1))
    m = re.search(rf"侍中((?:{SURNAMES})[一-龥]{{1,2}})(?:守|領|领|兼)?", s)
    if m:
        return norm(m.group(1))
    m = re.search(rf"以((?:{SURNAMES})[一-龥]{{1,2}})為侍中", s)
    if m:
        return norm(m.group(1))
    # 上下文本传
    opens = list(BIO_OPEN.finditer(ctx))
    if opens:
        return norm(opens[-1].group(1))
    m = re.search(rf"((?:{SURNAMES})[一-龥]{{1,2}})，字", ctx)
    if m:
        return norm(m.group(1))
    return None


def main() -> None:
    main_rows = {}
    with MAIN.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            # cand_row in queue is enumerate start=2 of original — map by index
            pass
    # 主表行号：DictReader 顺序 +2
    main_list = list(csv.DictReader(MAIN.open(encoding="utf-8-sig")))
    by_crow = {i: r for i, r in enumerate(main_list, start=2)}

    rows = list(csv.DictReader(QUEUE.open(encoding="utf-8-sig")))
    mined = defaultdict(list)
    miss = 0
    for r in rows:
        crow = int(r["cand_row"]) if str(r.get("cand_row", "")).isdigit() else None
        src = by_crow.get(crow, {}).get("source_file", "") if crow else ""
        sent = r.get("sentence") or ""
        ctx = load_ctx(src, sent) if src else sent
        person = guess(ctx, sent)
        if not person or len(person) < 2 or person in DENY:
            miss += 1
            continue
        mined[person].append(
            {
                "person": person,
                "cand_row": crow,
                "book": r.get("book"),
                "juan": r.get("juan"),
                "sentence": sent[:300],
                "source_file": src,
                "alias_in_sentence": "",
            }
        )
    print("mined", len(mined), "ev", sum(len(v) for v in mined.values()), "miss", miss)
    for p, evs in sorted(mined.items(), key=lambda x: -len(x[1]))[:50]:
        print(f"  {len(evs):2d} {p}")
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"],
        )
        w.writeheader()
        for p, evs in mined.items():
            for e in evs:
                w.writerow(e)
    print("->", OUT)


if __name__ == "__main__":
    main()
