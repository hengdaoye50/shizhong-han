"""从卡片引文/正文回填 nature 中的年号/帝号线索，提高时间轴上轴率。

原则：
- 仅当该人自己的 nature/quote/body 含明确年号或帝号时回填
- placeholder nature（见原典…）改写为可解析描述
- 已有实质 nature 则在末尾补「；XX时/XX中」若缺失
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import t2s

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

ERA = {
    "建武": (25, 56), "永平": (58, 75), "建初": (76, 84), "元和": (84, 87),
    "章和": (87, 88), "永元": (89, 105), "元兴": (105, 105), "延平": (106, 106),
    "永初": (107, 113), "元初": (114, 120), "永宁": (120, 121), "建光": (121, 122),
    "延光": (122, 125), "永建": (126, 132), "阳嘉": (132, 135), "永和": (136, 141),
    "汉安": (142, 144), "建康": (144, 144), "本初": (146, 146), "建和": (147, 149),
    "和平": (150, 150), "元嘉": (151, 153), "永兴": (153, 154), "永寿": (155, 158),
    "延熹": (158, 167), "永康": (167, 167), "建宁": (168, 172), "熹平": (172, 178),
    "光和": (178, 184), "中平": (184, 189), "初平": (190, 193), "兴平": (194, 195),
    "建安": (196, 220), "延康": (220, 220), "黄初": (220, 226), "太和": (227, 233),
    "青龙": (233, 237), "景初": (237, 239), "正始": (240, 249), "嘉平": (249, 254),
    "正元": (254, 256), "甘露": (256, 260), "景元": (260, 264), "咸熙": (264, 265),
    "泰始": (265, 274), "章武": (221, 223), "建兴": (223, 237), "延熙": (238, 257),
    "景耀": (258, 263), "黄武": (222, 229), "黄龙": (229, 231), "嘉禾": (232, 238),
    "赤乌": (238, 251), "元狩": (-122, -117), "元鼎": (-116, -111), "元封": (-110, -105),
    "太初": (-104, -101), "天汉": (-100, -97), "太始": (-96, -93), "征和": (-92, -89),
    "后元": (-88, -87), "始元": (-86, -80), "元凤": (-80, -75), "元平": (-74, -74),
    "本始": (-73, -70), "地节": (-69, -66), "元康": (-65, -62), "神爵": (-61, -58),
    "五凤": (-57, -54), "黄龙": (-49, -49), "初元": (-48, -44), "永光": (-43, -39),
    "建昭": (-38, -34), "竟宁": (-33, -33), "建始": (-32, -29), "河平": (-28, -25),
    "阳朔": (-24, -21), "鸿嘉": (-20, -17), "永始": (-16, -13), "元延": (-12, -9),
    "绥和": (-8, -7), "建平": (-6, -3), "元寿": (-2, -1), "元始": (1, 5),
}
EMP = {
    "高祖": (-202, -195), "惠帝": (-195, -188), "高后": (-188, -180), "吕后": (-188, -180),
    "文帝": None,  # 消歧
    "景帝": None, "武帝": (-141, -87), "昭帝": (-87, -74), "宣帝": (-74, -49),
    "元帝": None, "成帝": (-33, -7), "哀帝": (-7, -1), "平帝": (1, 5),
    "王莽": (9, 23), "更始": (23, 25), "更始帝": (23, 25),
    "光武": (25, 57), "光武帝": (25, 57), "明帝": (58, 75), "章帝": (76, 88),
    "和帝": (89, 105), "殇帝": (106, 106), "安帝": (107, 125), "顺帝": (126, 144),
    "冲帝": (145, 145), "质帝": (146, 146), "桓帝": (147, 167), "灵帝": (168, 189),
    "少帝": (189, 189), "献帝": (189, 220),
}
# 帝号按朝代
EMP_BY_DYN = {
    "文帝": {"西汉": (-180, -157), "魏": (220, 226), "default": (-180, -157)},
    "景帝": {"西汉": (-157, -141), "吴": (258, 264), "default": (-157, -141)},
    "元帝": {"西汉": (-49, -33), "魏": (260, 265), "default": (-49, -33)},
    "明帝": {"东汉": (58, 75), "魏": (227, 239), "default": (58, 75)},
}

PLACEHOLDER = ("见原典", "有明文", "待补", "见原典「侍中」明文")


def parse_card(p: Path):
    t = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S)
    if not m:
        return None
    return m.group(1), m.group(2)


def grab(fm, k):
    mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
    return mm.group(1).strip() if mm else ""


def first_nature(fm: str) -> str:
    in_t = False
    for line in fm.splitlines():
        if line.startswith("shizhong_terms:"):
            in_t = True
            continue
        if in_t:
            s = line.strip()
            if s.startswith("nature:"):
                return s.split(":", 1)[1].strip()
            if line and not line[0].isspace() and not line.strip().startswith("-"):
                break
    return ""


def find_era(text: str):
    best = None
    for era in ERA:
        if era not in text:
            continue
        # 优先带「中/初/间/年」
        m = re.search(era + r"([元一二三四五六七八九十\d]+年|[初中末间間]?)", text)
        mod = m.group(1) if m else ""
        y0, y1 = ERA[era]
        if mod and mod not in ("中", "初", "末", "间", "間", ""):
            # 有年数
            label = era + mod if mod.endswith("年") else era + mod + "年"
        elif mod in ("初",):
            label = era + "初"
        elif mod in ("中",):
            label = era + "中"
        elif mod in ("末",):
            label = era + "末"
        elif mod in ("间", "間"):
            label = era + "间"
        else:
            label = era
        # 记录最先出现的
        if best is None:
            best = (label, era)
    return best


def find_emp(text: str, dynasty: str):
    # 长名优先
    keys = sorted(
        ["光武帝", "更始帝", "高后", "吕后", "光武", "昭烈", "后主", "大帝", "王莽",
         "高祖", "惠帝", "文帝", "景帝", "武帝", "昭帝", "宣帝", "元帝", "成帝",
         "哀帝", "平帝", "明帝", "章帝", "和帝", "殇帝", "安帝", "顺帝", "冲帝",
         "质帝", "桓帝", "灵帝", "少帝", "献帝", "更始"],
        key=len,
        reverse=True,
    )
    for k in keys:
        if k not in text:
            continue
        window = ""
        idx = text.find(k)
        window = text[max(0, idx - 2) : idx + len(k) + 6]
        if k in EMP_BY_DYN:
            span = EMP_BY_DYN[k].get(dynasty) or EMP_BY_DYN[k].get("default")
        else:
            span = EMP.get(k)
        if not span:
            continue
        if "即位" in window or "即位" in text[idx : idx + len(k) + 4]:
            return f"{k}即位", span[0], span[0]
        if "崩" in window:
            return f"{k}崩时", span[1], span[1]
        if "初" in text[idx + len(k) : idx + len(k) + 2]:
            return f"{k}初", span[0], span[0] + max(1, (span[1] - span[0]) // 3)
        return f"{k}时", span[0], span[1]
    return None


def main() -> None:
    # 先标记已上轴者
    tl = (ROOT / "shizhongdata/data/timeline.json").read_text(encoding="utf-8")
    import json

    plotted = {it["id"] for it in json.loads(tl)["items"]}

    updated_cards = 0
    updates = []  # (pid, nature)

    for p in sorted(CARDS.glob("*.md")):
        parsed = parse_card(p)
        if not parsed:
            continue
        fm, body = parsed
        pid, name = grab(fm, "id"), grab(fm, "name")
        if not pid or pid in plotted:
            continue
        dyn = grab(fm, "dynasty")
        nature = first_nature(fm)
        quotes = re.findall(r"^\s+quote:\s*(.*)$", fm, re.M)
        blob = t2s(" ".join([nature] + quotes + [body[:1200]]))

        era = find_era(blob)
        emp = find_emp(blob, dyn)

        # 选择线索：年号优先
        clue = None
        if era:
            clue = era[0]
        elif emp:
            clue = emp[0]

        if not clue:
            continue

        is_ph = (not nature) or any(nature.startswith(x) or nature == x for x in PLACEHOLDER) or "见原典" in nature

        if is_ph:
            new_nature = f"{clue}侍中"
            # 替换 nature 行
            new_fm = re.sub(
                r"(shizhong_terms:\n(?:  - .*\n(?:    .*\n)*)?    nature:\s*)(.*)",
                lambda m: m.group(1) + new_nature,
                fm,
                count=1,
            )
            if new_fm != fm:
                p.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")
                updated_cards += 1
                updates.append((pid, new_nature, name))
        else:
            # 已有 nature：若无年号/帝号词则追加
            has_era = any(e in nature for e in ERA)
            has_emp = any(
                k in nature for k in list(EMP_BY_DYN) + [k for k, v in EMP.items() if v]
            )
            if not has_era and not has_emp:
                new_nature = nature.rstrip("；;") + "；" + clue
                new_fm = re.sub(
                    r"(shizhong_terms:\n(?:  - .*\n(?:    .*\n)*)?    nature:\s*)(.*)",
                    lambda m: m.group(1) + new_nature,
                    fm,
                    count=1,
                )
                if new_fm != fm:
                    p.write_text(f"---\n{new_fm}\n---\n{body}", encoding="utf-8")
                    updated_cards += 1
                    updates.append((pid, new_nature, name))

    print(f"cards updated {updated_cards}")

    # 同步 DB nature
    con = sqlite3.connect(DB)
    cur = con.cursor()
    for pid, nature, name in updates:
        cur.execute("UPDATE shizhong_term SET nature=? WHERE person_id=?", (nature[:160], pid))
    con.commit()
    con.close()
    print(f"db terms updated {len(updates)}")
    for pid, nature, name in updates[:15]:
        print(f"  {name}: {nature}")


if __name__ == "__main__":
    main()
