"""上下文回读：对 unparsed 队列，从 source_file 取前后文，尝试解析本传/本句主语。

输出 candidates/persons_context_mined.csv
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "candidates" / "unparsed_namequeue.csv"
OUT = ROOT / "data" / "candidates" / "persons_context_mined.csv"

SURNAMES = (
    "霍|金|上官|桑|杨|楊|张|張|王|李|赵|趙|陈|陳|刘|劉|邓|鄧|耿|窦|竇|马|馬|班|梁|袁|曹|"
    "孙|孫|周|吴|吳|郑|鄭|朱|许|許|冯|馮|董|萧|蕭|程|傅|贾|賈|夏侯|诸葛|諸葛|司马|司馬|"
    "皇甫|鲁|魯|尹|何|郭|阴|陰|来|來|岑|任|宋|杜|桓|虞|黄|黃|蔡|荀|孔|钟|鍾|华|華|卫|衛|"
    "陆|陸|顾|顧|纪|紀|徐|谢|謝|韩|韓|唐|石|白|侯|段|汪|田|姚|毛|秦|江|史|黎|乔|喬|龚|龔|"
    "于|於|齐|齊|康|伍|余|元|刁|单|單|施|丁|贺|郗|习|習|滕|是|濮|步|阙|闕|灌|祭|铫|銚"
)

# 本传常见开头：「X字Y」「X，某地人」
BIO_OPEN = re.compile(rf"((?:{SURNAMES})[一-龥]{{1,2}})(?:字[一-龥]{{1,3}}|[，,][一-龥]{{0,6}}人也)")

T2S = str.maketrans({
    "劉": "刘", "張": "张", "楊": "杨", "趙": "赵", "陳": "陈", "鄧": "邓",
    "竇": "窦", "馬": "马", "孫": "孙", "鄭": "郑", "許": "许", "馮": "冯",
    "蕭": "萧", "賈": "贾", "魯": "鲁", "陰": "阴", "來": "来", "黃": "黄",
    "鍾": "钟", "華": "华", "衛": "卫", "陸": "陆", "顧": "顾", "紀": "纪",
    "韓": "韩", "謝": "谢", "龔": "龚", "喬": "乔", "齊": "齐", "單": "单",
    "習": "习", "闕": "阙",
})


def norm(n: str) -> str:
    return n.translate(T2S).strip()


def load_context(sf: str, sentence: str) -> str:
    p = ROOT / sf if not Path(sf).is_absolute() else Path(sf)
    if not p.exists():
        return sentence
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return sentence
    key = sentence.replace(" ", "")[:20]
    # 简化搜索：取句子前 12 字
    frag = re.sub(r"[「」『』\[\]（）()]", "", key)[:12]
    idx = text.find(frag)
    if idx < 0:
        frag2 = re.sub(r"[「」『』\[\]（）()]", "", sentence.replace(" ", ""))[:8]
        idx = text.find(frag2)
    if idx < 0:
        return sentence
    return text[max(0, idx - 400) : idx + 200]


def guess_subject(ctx: str, sentence: str) -> str | None:
    # 1) 上下文里的「X字Y」
    opens = list(BIO_OPEN.finditer(ctx))
    if opens:
        return norm(opens[-1].group(1))
    # 2) 本句「以X为侍中」「X为侍中」
    m = re.search(rf"((?:{SURNAMES})[一-龥]{{1,2}})(?:为|為|拜|遷|迁|稍遷)侍中", sentence.replace(" ", ""))
    if m:
        return norm(m.group(1))
    m = re.search(rf"侍中((?:{SURNAMES})[一-龥]{{1,2}})", sentence.replace(" ", ""))
    if m:
        return norm(m.group(1))
    # 3) 上下文近处「X，字」
    m = re.search(rf"((?:{SURNAMES})[一-龥]{{1,2}})，字", ctx)
    if m:
        return norm(m.group(1))
    return None


def main() -> None:
    rows = list(csv.DictReader(QUEUE.open(encoding="utf-8-sig")))
    mined = defaultdict(list)
    miss = 0
    for r in rows:
        sent = r.get("sentence") or ""
        ctx = load_context(r.get("source_file") or "", sent)
        person = guess_subject(ctx, sent)
        if not person or len(person) < 2:
            miss += 1
            continue
        # 过滤官名
        if person in {"侍中", "尚书", "将军", "黄门", "于是", "更始", "光武", "顺帝", "和帝", "安帝", "桓帝", "灵帝", "献帝", "肃宗", "显宗"}:
            miss += 1
            continue
        mined[person].append(
            {
                "person": person,
                "cand_row": r.get("cand_row"),
                "book": r.get("book"),
                "juan": r.get("juan"),
                "sentence": sent[:300],
                "source_file": r.get("source_file", ""),
                "alias_in_sentence": "",
            }
        )
    print("context mined", len(mined), "ev", sum(len(v) for v in mined.values()), "miss", miss)
    for p, evs in sorted(mined.items(), key=lambda x: -len(x[1]))[:40]:
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
