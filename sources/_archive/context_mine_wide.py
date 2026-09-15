"""更宽上下文挖人：扩大窗口 + 任职动词 + 本传标题（章名含人名）。"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "candidates" / "unparsed_namequeue.csv"
MAIN = ROOT / "data" / "candidates" / "shizhong_candidates.csv"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
OUT = ROOT / "data" / "candidates" / "persons_context_wide.csv"

SURNAMES = (
    "霍|金|上官|桑|杨|楊|张|張|王|李|赵|趙|陈|陳|刘|劉|邓|鄧|耿|窦|竇|马|馬|班|梁|袁|曹|"
    "孙|孫|周|吴|吳|郑|鄭|朱|许|許|冯|馮|董|萧|蕭|程|傅|贾|賈|夏侯|诸葛|諸葛|司马|司馬|"
    "皇甫|鲁|魯|尹|何|郭|阴|陰|来|來|岑|任|宋|杜|桓|虞|黄|黃|蔡|荀|孔|钟|鍾|华|華|卫|衛|"
    "陆|陸|顾|顧|纪|紀|徐|谢|謝|韩|韓|唐|石|白|侯|段|汪|田|姚|毛|秦|江|史|黎|乔|喬|龚|龔|"
    "于|於|齐|齊|康|伍|余|元|刁|单|單|施|丁|贺|郗|习|習|滕|是|步|灌|祭|铫|銚|濮|淳于|申屠|"
    "公孙|公孫|第五|毋|兒|儿|奚|嵇|阮|向"
)

NAME = rf"((?:{SURNAMES})[一-龥]{{1,2}})"

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
    "卫青者", "卫皇后", "是正文", "孙皓", "朱建平", "乔卿", "元以来", "郭玉者",
    "王朝", "祭酒", "光禄", "大夫", "中郎", "仆射", "校尉", "长史", "参军",
}


def norm(n: str) -> str:
    n = n.translate(T2S).strip()
    for suf in ("者", "等", "曰", "书", "書", "奏", "言", "上", "下"):
        if len(n) > 2 and n.endswith(suf):
            n = n[: -len(suf)]
    return n


def load_file(sf: str) -> str:
    p = ROOT / sf
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore")


def find_span(text: str, sentence: str) -> tuple[int, int]:
    frag = re.sub(r"[「」『』\[\]（）()\s0-9]", "", sentence)[:12]
    idx = text.find(frag)
    if idx < 0:
        frag = frag[:8]
        idx = text.find(frag)
    if idx < 0:
        return -1, -1
    return max(0, idx - 800), min(len(text), idx + 400)


def guess_all(text: str, span: tuple[int, int], sentence: str) -> list[str]:
    a, b = span
    ctx = text[a:b] if a >= 0 else sentence
    s = sentence.replace(" ", "")
    found = []

    # 句内优先
    pats = [
        rf"{NAME}(?:为|為|拜|遷|迁|稍遷|稍迁|復為|复为|再為|再为|徵|征)侍中",
        rf"以{NAME}(?:为|為)侍中",
        rf"侍中{NAME}(?:守|領|领|兼|行)?",
        rf"(?:拜|徵|征|迁|遷|擢|复|復|再|入|出){NAME}(?:为|為)侍中",
    ]
    for pat in pats:
        for m in re.finditer(pat, s):
            n = norm(m.group(1))
            if 2 <= len(n) <= 4 and n not in DENY:
                found.append(n)

    # 上下文本传：X字Y / X，某地人
    for m in re.finditer(rf"{NAME}(?:字[一-龥]{{1,3}}|[，,][一-龥]{{0,8}}人也)", ctx):
        n = norm(m.group(1))
        if 2 <= len(n) <= 4 and n not in DENY:
            found.append(n)

    # 章名：如「桓荣丁鸿列传」→ 桓荣
    juan_m = re.search(r"第[一二三四五六七八九十百零〇\d]+章[:：]([一-龥]+)", sentence)  # unlikely
    # source juan 常是「第三十一章:刘赵淳于江刘周赵列传」——由调用方传入更好
    # 近处「X，字」
    for m in re.finditer(rf"{NAME}，字", ctx):
        n = norm(m.group(1))
        if 2 <= len(n) <= 4 and n not in DENY:
            found.append(n)

    # 去重
    res, seen = [], set()
    for n in found:
        if n not in seen:
            seen.add(n)
            res.append(n)
    return res


def main() -> None:
    main_list = list(csv.DictReader(MAIN.open(encoding="utf-8-sig")))
    by_crow = {i: r for i, r in enumerate(main_list, start=2)}

    # 已有 evidence 人名
    have_persons = set()
    if EV.exists():
        with EV.open(encoding="utf-8-sig") as f:
            have_persons = {r["person"] for r in csv.DictReader(f)}

    rows = list(csv.DictReader(QUEUE.open(encoding="utf-8-sig")))
    mined = defaultdict(list)
    multi = 0
    for r in rows:
        crow = int(r["cand_row"]) if str(r.get("cand_row", "")).isdigit() else None
        src = by_crow.get(crow, {}).get("source_file", "") if crow else ""
        juan = r.get("juan") or ""
        sent = r.get("sentence") or ""
        text = load_file(src) if src else ""
        span = find_span(text, sent) if text else (-1, -1)
        names = guess_all(text, span, sent)
        # 章名启发：juan「第三十一章:刘赵淳于江刘周赵列传」→ 取「刘」「赵」等太碎，跳过
        if not names:
            continue
        if len(names) > 1:
            multi += 1
        # 取最可能的 1-2 个：优先句内命中者
        use = names[:2]
        for n in use:
            if n in have_persons:
                continue
            mined[n].append(
                {
                    "person": n,
                    "cand_row": crow,
                    "book": r.get("book"),
                    "juan": juan,
                    "sentence": sent[:300],
                    "source_file": src,
                    "alias_in_sentence": "",
                }
            )

    print("new persons (not already in ev)", len(mined), "ev", sum(len(v) for v in mined.values()))
    for p, evs in sorted(mined.items(), key=lambda x: -len(x[1]))[:60]:
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
