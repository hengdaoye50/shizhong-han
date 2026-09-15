"""按 mirror 章节文件：文件名含人名列传 → 文内「侍中」→ 归属到该传主。"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / "data" / "raw" / "mirror" / "後漢書"
OUT = ROOT / "data" / "candidates" / "persons_biography_scan.csv"

# 「第X章-人名列传-原文」→ 人名列表
# 如 第二十九章-桓荣丁鸿列传
TITLE = re.compile(r"第[一二三四五六七八九十百零〇\d]+章-(.+?)(?:列传|傳|纪|紀|表|志)")

# 从「桓荣丁鸿列传」拆名
SURNAMES = (
    "霍|金|上官|桑|杨|楊|张|張|王|李|赵|趙|陈|陳|刘|劉|邓|鄧|耿|窦|竇|马|馬|班|梁|袁|曹|"
    "孙|孫|周|吴|吳|郑|鄭|朱|许|許|冯|馮|董|萧|蕭|程|傅|贾|賈|夏侯|诸葛|諸葛|司马|司馬|"
    "皇甫|鲁|魯|尹|何|郭|阴|陰|来|來|岑|任|宋|杜|桓|虞|黄|黃|蔡|荀|孔|钟|鍾|华|華|卫|衛|"
    "陆|陸|顾|顧|纪|紀|徐|谢|謝|韩|韓|唐|石|白|侯|段|汪|田|姚|毛|秦|江|史|黎|乔|喬|龚|龔|"
    "于|於|齐|齊|康|伍|余|元|刁|单|單|施|丁|贺|郗|习|習|滕|是|步|灌|祭|铫|銚|濮|淳于|申屠"
)


CLASS_TITLES = {
    "儒林", "宦者", "方术", "文苑", "独行", "党锢", "酷吏", "循吏",
    "皇后", "外戚", "宗室", "列女", "逸民", "东夷", "南蛮", "西羌",
    "西域", "乌桓", "鲜卑", "匈奴", "孝献", "孝灵", "孝桓", "孝质",
    "孝冲", "孝顺", "孝安", "孝和", "孝殇", "孝章", "孝明", "孝景",
    "光武", "显宗", "肃宗",
}


def split_title_names(title: str) -> list[str]:
    """从「桓荣丁鸿」「刘赵淳于江刘周赵」拆出人名。"""
    s = title
    s = re.sub(r"(列传|傳|纪|紀|表|志).*$", "", s)
    if s in CLASS_TITLES:
        return []
    names = []
    i = 0
    while i < len(s):
        matched = False
        for two in ("淳于", "申屠", "夏侯", "诸葛", "諸葛", "司马", "司馬", "皇甫", "公孙", "公孫"):
            if s.startswith(two, i) and i + 3 <= len(s):
                names.append(s[i : i + 3])
                i += 3
                matched = True
                break
        if matched:
            continue
        if i + 2 <= len(s):
            names.append(s[i : i + 2])
            i += 2
        else:
            break
    return [n for n in names if n not in CLASS_TITLES and len(n) >= 2]


def main() -> None:
    out_rows = []
    if not MIRROR.exists():
        print("no mirror", MIRROR)
        return
    files = list(MIRROR.rglob("*原文*.txt")) + list(MIRROR.rglob("*.txt"))
    # 去重
    files = sorted(set(files))
    for fp in files:
        m = TITLE.search(fp.stem)
        if not m:
            continue
        title = m.group(1)
        persons = split_title_names(title)
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "侍中" not in text:
            continue
        # 句子级
        for sent in re.split(r"(?<=[。！？；])", text):
            if "侍中" not in sent:
                continue
            sent = sent.strip()
            if len(sent) < 6:
                continue
            # 归属：句中出现传主名，或整传只有一主
            hit = [p for p in persons if p in sent]
            if not hit:
                # 整章侍中句，记到传主们（取前1-2）
                if len(persons) == 1:
                    hit = persons
                else:
                    continue
            for p in hit[:2]:
                out_rows.append(
                    {
                        "person": p,
                        "book": "後漢書",
                        "juan": fp.stem[:40],
                        "sentence": sent[:300],
                        "source_file": str(fp.relative_to(ROOT)).replace("\\", "/"),
                        "title_persons": "、".join(persons),
                    }
                )
    print("rows", len(out_rows), "persons", len({r["person"] for r in out_rows}))
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()) if out_rows else ["person"])
        w.writeheader()
        w.writerows(out_rows)
    # top
    from collections import Counter
    c = Counter(r["person"] for r in out_rows)
    print("top30", c.most_common(30))
    print("->", OUT)


if __name__ == "__main__":
    main()
