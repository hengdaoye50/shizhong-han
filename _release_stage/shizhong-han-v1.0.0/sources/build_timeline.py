"""从卡片重建时间轴数据：按精确度分级，不为仅知朝代者伪造区间。

精度三级（对外展示）：
  exact  — 生卒年可考（可画寿命；若有侍中年号另标）
  era    — 有年号纪年（建武二十年 / 嘉禾中 / 永平初）
  reign  — 仅知帝号在位期（灵帝时 / 光武即位）
  dynasty— 仅知朝代，不画个人横条，只进朝代聚合

输出 shizhongdata/data/timeline.json，并回写 person 年代列（不覆盖 nature 原文）。
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import t2s

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"
OUT = ROOT / "shizhongdata" / "data" / "timeline.json"

# ---------------------------------------------------------------------------
# 朝代色带窗口
# ---------------------------------------------------------------------------
DYN_WINDOW = {
    "西漢": (-202, 8),
    "新": (9, 23),
    "更始": (23, 25),
    "東漢": (25, 220),
    "漢魏之際": (190, 230),
    "魏": (220, 265),
    "蜀漢": (221, 263),
    "吳": (222, 280),
    "晉": (265, 300),
    "西漢_新": (-202, 23),
    "更始_東漢": (23, 220),
    "西漢_東漢": (-202, 220),
    "兩漢": (-202, 220),
    "蜀漢_魏": (221, 265),
    "魏_晉": (220, 300),
}

BANDS = [
    {"name": "西汉", "start": -202, "end": 8},
    {"name": "新", "start": 9, "end": 23},
    {"name": "东汉", "start": 25, "end": 220},
    {"name": "魏", "start": 220, "end": 265},
    {"name": "蜀汉", "start": 221, "end": 263},
    {"name": "吴", "start": 222, "end": 280},
]

# ---------------------------------------------------------------------------
# 帝号 → 在位区间（用于「X帝时」）
# 同名帝号用带朝代前缀的规范键，见 resolve_emperor
# ---------------------------------------------------------------------------
EMPERORS_CANON = {
    "高祖": ("西漢", -202, -195),
    "惠帝": ("西漢", -195, -188),
    "高后": ("西漢", -188, -180),
    "吕后": ("西漢", -188, -180),
    "西漢文帝": ("西漢", -180, -157),
    "西漢景帝": ("西漢", -157, -141),
    "武帝": ("西漢", -141, -87),
    "昭帝": ("西漢", -87, -74),
    "宣帝": ("西漢", -74, -49),
    "西漢元帝": ("西漢", -49, -33),
    "成帝": ("西漢", -33, -7),
    "哀帝": ("西漢", -7, -1),
    "平帝": ("西漢", 1, 5),
    "王莽": ("新", 9, 23),
    "更始": ("更始", 23, 25),
    "更始帝": ("更始", 23, 25),
    "光武": ("東漢", 25, 57),
    "光武帝": ("東漢", 25, 57),
    "東漢明帝": ("東漢", 58, 75),
    "章帝": ("東漢", 76, 88),
    "和帝": ("東漢", 89, 105),
    "殇帝": ("東漢", 106, 106),
    "安帝": ("東漢", 107, 125),
    "顺帝": ("東漢", 126, 144),
    "冲帝": ("東漢", 145, 145),
    "质帝": ("東漢", 146, 146),
    "桓帝": ("東漢", 147, 167),
    "灵帝": ("東漢", 168, 189),
    "少帝": ("東漢", 189, 189),
    "献帝": ("東漢", 189, 220),
    "魏文帝": ("魏", 220, 226),
    "魏明帝": ("魏", 227, 239),
    "齐王": ("魏", 240, 253),
    "高贵乡公": ("魏", 254, 259),
    "魏元帝": ("魏", 260, 265),
    "曹丕": ("魏", 220, 226),
    "曹叡": ("魏", 227, 239),
    "曹芳": ("魏", 240, 253),
    "曹髦": ("魏", 254, 259),
    "曹奂": ("魏", 260, 265),
    "昭烈": ("蜀漢", 221, 223),
    "刘备": ("蜀漢", 221, 223),
    "后主": ("蜀漢", 223, 263),
    "刘禅": ("蜀漢", 223, 263),
    "大帝": ("吳", 222, 252),
    "孙权": ("吳", 222, 252),
    "会稽王": ("吳", 252, 258),
    "孙亮": ("吳", 252, 258),
    "吳景帝": ("吳", 258, 264),
    "孙休": ("吳", 258, 264),
    "末帝": ("吳", 264, 280),
    "孙皓": ("吳", 264, 280),
}

# 帝号扫描顺序（长名优先，避免「光武帝」被「光武」截断后误判）
EMPEROR_KEYS = sorted(EMPERORS_CANON.keys(), key=len, reverse=True)

# ---------------------------------------------------------------------------
# 年号 → 起始公元年（含大致跨度，供「初/中/间」）
# value: (start, end)  end = start + typical_len - 1
# ---------------------------------------------------------------------------
ERA_SPAN: dict[str, tuple[int, int]] = {
    # 西漢
    "元狩": (-122, -117), "元鼎": (-116, -111), "元封": (-110, -105),
    "太初": (-104, -101), "天汉": (-100, -97), "太始": (-96, -93),
    "征和": (-92, -89), "后元": (-88, -87), "始元": (-86, -80),
    "元凤": (-80, -75), "元平": (-74, -74), "本始": (-73, -70),
    "地节": (-69, -66), "元康": (-65, -62), "神爵": (-61, -58),
    "五凤": (-57, -54), "甘露": (-53, -50), "黄龙": (-49, -49),
    "初元": (-48, -44), "永光": (-43, -39), "建昭": (-38, -34),
    "竟宁": (-33, -33), "建始": (-32, -29), "河平": (-28, -25),
    "阳朔": (-24, -21), "鸿嘉": (-20, -17), "永始": (-16, -13),
    "元延": (-12, -9), "绥和": (-8, -7), "建平": (-6, -3),
    "元寿": (-2, -1), "元始": (1, 5), "居摄": (6, 8), "初始": (8, 8),
    # 東漢
    "建武": (25, 56), "建武中元": (56, 57), "永平": (58, 75),
    "建初": (76, 84), "元和": (84, 87), "章和": (87, 88),
    "永元": (89, 105), "元兴": (105, 105), "延平": (106, 106),
    "永初": (107, 113), "元初": (114, 120), "永宁": (120, 121),
    "建光": (121, 122), "延光": (122, 125), "永建": (126, 132),
    "阳嘉": (132, 135), "永和": (136, 141), "汉安": (142, 144),
    "建康": (144, 144), "永憙": (145, 145), "本初": (146, 146),
    "建和": (147, 149), "和平": (150, 150), "元嘉": (151, 153),
    "永兴": (153, 154), "永寿": (155, 158), "延熹": (158, 167),
    "永康": (167, 167), "建宁": (168, 172), "熹平": (172, 178),
    "光和": (178, 184), "中平": (184, 189), "初平": (190, 193),
    "兴平": (194, 195), "建安": (196, 220), "延康": (220, 220),
    # 魏
    "黄初": (220, 226), "太和": (227, 233), "青龙": (233, 237),
    "景初": (237, 239), "正始": (240, 249), "嘉平": (249, 254),
    "正元": (254, 256), "甘露": (256, 260), "景元": (260, 264),
    "咸熙": (264, 265),
    # 蜀
    "章武": (221, 223), "建兴": (223, 237), "延熙": (238, 257),
    "景耀": (258, 263), "炎兴": (263, 263),
    # 吳
    "黄武": (222, 229), "黄龙": (229, 231), "嘉禾": (232, 238),
    "赤乌": (238, 251), "太元": (251, 252), "神凤": (252, 252),
    "建兴": (252, 253),  # 吳建兴；与蜀建兴冲突，解析时按朝代消歧
    "五凤": (253, 254), "太平": (254, 256), "永安": (258, 264),
    "元兴": (264, 265), "甘露": (265, 266), "宝鼎": (266, 269),
    "建衡": (269, 271), "凤凰": (272, 274), "天册": (275, 276),
    "天玺": (276, 276), "天纪": (277, 280),
}

# 年号消歧：同名年号按朝代
ERA_DYN = {
    "建兴": {"蜀漢": ("蜀漢", 223, 237), "吳": ("吳", 252, 253), "default": ("蜀漢", 223, 237)},
    "甘露": {"西漢": ("西漢", -53, -50), "魏": ("魏", 256, 260), "吳": ("吳", 265, 266), "default": ("西漢", -53, -50)},
    "黄龙": {"西漢": ("西漢", -49, -49), "吳": ("吳", 229, 231), "default": ("西漢", -49, -49)},
    "元兴": {"東漢": ("東漢", 105, 105), "吳": ("吳", 264, 265), "default": ("東漢", 105, 105)},
    "五凤": {"西漢": ("西漢", -57, -54), "吳": ("吳", 253, 254), "default": ("西漢", -57, -54)},
}

ERA_KEYS = sorted(ERA_SPAN.keys(), key=len, reverse=True)

CN_NUM = {
    "元": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
    "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
    "十六": 16, "十七": 17, "十八": 18, "十九": 19, "二十": 20,
    "廿": 20, "卅": 30,
}

# 占位 nature：不算年代线索
PLACEHOLDER_NATURE = ("见原典「侍中」明文", "见原典", "有明文", "待补", "")


def parse_year(s: str):
    if not s:
        return None
    s = s.strip()
    if s in ("阙", "—", "-", "？", "?", "不详", "未知"):
        return None
    m = re.match(r"^前(\d+)", s)
    if m:
        return -int(m.group(1))
    m = re.match(r"^(\d{1,4})$", s)
    if m:
        return int(m.group(1))
    m = re.search(r"(前)?(\d{3,4})", s)
    if m:
        y = int(m.group(2))
        if y <= 300:
            return -y if m.group(1) else y
    return None


def _cn_to_int(tok: str) -> int | None:
    if not tok:
        return None
    if tok.isdigit():
        return int(tok)
    if tok in CN_NUM:
        return CN_NUM[tok]
    # 二十 / 十二 等简单组合
    if tok.startswith("二十"):
        rest = tok[2:]
        return 20 + (CN_NUM.get(rest, 0) if rest else 0)
    if tok.startswith("十"):
        rest = tok[1:]
        return 10 + (CN_NUM.get(rest, 0) if rest else 0)
    return None


def parse_era(nature: str, dynasty: str = ""):
    """从 nature 抽年号纪年。

    返回 (year, label, span_end) 或 None。
    - 「建武二十年」→ (44, '建武二十年', 44)
    - 「永平初」→ (58, '永平初', 63)
    - 「嘉禾中」→ (234, '嘉禾中', 236)
    - 「建安间」→ (196, '建安间', 220)
    """
    if not nature or nature.strip() in PLACEHOLDER_NATURE:
        return None
    # 先消歧再匹配：按人物朝代选年号
    candidates = []
    for era in ERA_KEYS:
        if era not in nature:
            continue
        if era in ERA_DYN:
            dyn_map = ERA_DYN[era]
            span = dyn_map.get(dynasty) or dyn_map.get("default")
            y0, y1 = span[1], span[2]
        else:
            y0, y1 = ERA_SPAN[era]
        candidates.append((era, y0, y1))
    if not candidates:
        return None
    # 取 nature 中最先出现的年号
    candidates.sort(key=lambda x: nature.find(x[0]))
    era, y0, y1 = candidates[0]
    idx = nature.find(era)
    tail = nature[idx + len(era) : idx + len(era) + 6]

    # 明确年：元年 / 二十年 / 2年
    m = re.match(r"([元一二三四五六七八九十廿卅]+|\d+)\s*年", tail)
    if m:
        n = _cn_to_int(m.group(1))
        if n:
            y = y0 + n - 1
            return y, f"{era}{m.group(1)}年", y

    # 初 / 中 / 末 / 间 / 岁
    if re.match(r"初", tail):
        span = max(1, (y1 - y0 + 1) // 3)
        return y0, f"{era}初", y0 + span - 1
    if re.match(r"中", tail) or re.search(rf"{era}中", nature):
        mid = (y0 + y1) // 2
        return mid, f"{era}中", mid
    if re.match(r"末", tail):
        return max(y0, y1 - 2), f"{era}末", y1
    if re.match(r"间|間", tail):
        return y0, f"{era}间", y1

    # 「X帝建平中」：年号后无修饰，整段
    return y0, era, y1


def resolve_emperor(nature: str, dynasty: str = ""):
    """从 nature 抽帝号在位期。

    返回 (start, end, label, kind) 或 None。
    kind: 'reign' 整段在位 | 'accession' 即位 | 'demise' 崩时
    """
    if not nature or nature.strip() in PLACEHOLDER_NATURE:
        return None
    # 长名优先
    for key in EMPEROR_KEYS:
        if key not in nature:
            continue
        # 同名消歧
        canon = key
        if key in ("文帝", "明帝", "元帝", "景帝"):
            if dynasty in ("西漢", "西汉"):
                if key == "文帝":
                    canon = "西漢文帝"
                elif key == "景帝":
                    canon = "西漢景帝"
                elif key == "元帝":
                    canon = "西漢元帝"
                elif key == "明帝":
                    # 西漢无明帝
                    continue
            elif dynasty in ("魏",):
                if key == "文帝":
                    canon = "魏文帝"
                elif key == "明帝":
                    canon = "魏明帝"
                elif key == "元帝":
                    canon = "魏元帝"
                elif key == "景帝":
                    continue
            elif dynasty in ("東漢", "東汉", "更始_東漢"):
                if key == "明帝":
                    canon = "東漢明帝"
                elif key in ("文帝", "元帝", "景帝"):
                    continue
            elif dynasty in ("吳", "吴"):
                if key == "景帝":
                    canon = "吳景帝"
                elif key in ("文帝", "明帝", "元帝"):
                    # 吳无这些帝号作年号语境时仍可能是魏/蜀人物跨朝，跳过
                    continue
        info = EMPERORS_CANON.get(canon)
        if not info:
            continue
        _, y0, y1 = info
        idx = nature.find(key)
        window = nature[max(0, idx - 2) : idx + len(key) + 6]
        if "即位" in nature[idx : idx + len(key) + 6] or "即位" in window:
            return y0, y0, f"{key}即位", "accession"
        if "崩时" in nature[idx : idx + len(key) + 6] or "崩" in window:
            return y1, y1, f"{key}崩时", "demise"
        return y0, y1, f"{key}时", "reign"
    return None


def parse_age_term(nature: str, birth: int | None):
    """「年十八为侍中」+ 生卒 → 推任职年。返回 (year, label) 或 None。"""
    if not nature or birth is None:
        return None
    m = re.search(r"年([元一二三四五六七八九十]+|\d+)(?:岁|歲)?\s*(?:为|為|拜|稍|再|迁|遷)?\s*侍中", nature)
    if not m:
        # 更宽：年十八
        m = re.search(r"年([元一二三四五六七八九十]{1,3}|\d{1,2})", nature)
        if not m:
            return None
    n = _cn_to_int(m.group(1))
    if not n or n > 60:
        return None
    return birth + n, f"年{n}"


def parse_aiping(nature: str):
    """「哀、平间 / 哀平间」→ 哀帝至平帝。"""
    if not nature:
        return None
    if re.search(r"哀\s*[、，,]?\s*平\s*(间|間)", nature) or "哀平" in nature:
        return -7, 5, "哀平间"
    return None


def shizhong_segment(nature: str) -> str:
    """优先取含「侍中」的分句，避免被后续官职年号带偏。"""
    if not nature:
        return ""
    parts = re.split(r"[；;。]", nature)
    for p in parts:
        if "侍中" in p:
            return p.strip()
    return nature


def parse_card(p: Path):
    t = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S)
    if not m:
        return None
    fm = m.group(1)

    def grab(k):
        mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
        return mm.group(1).strip() if mm else ""

    nature = ""
    in_t = False
    for line in fm.splitlines():
        if line.startswith("shizhong_terms:"):
            in_t = True
            continue
        if in_t:
            s = line.strip()
            if s.startswith("nature:"):
                nature = s.split(":", 1)[1].strip()
                break
            if line and not line[0].isspace() and not line.strip().startswith("-"):
                break
    return {
        "id": grab("id"),
        "name": grab("name"),
        "dynasty": t2s(grab("dynasty")),
        "style_name": grab("style_name"),
        "category": grab("category"),
        "birth": grab("birth"),
        "death": grab("death"),
        "nature": nature,
        "status": grab("status"),
    }


def classify(c: dict) -> dict:
    """给单人打精度与可画窗口。"""
    name = c["name"]
    dyn = c["dynasty"]
    nature = c["nature"] or ""
    by = parse_year(c["birth"])
    dy = parse_year(c["death"])

    # 优先在含「侍中」的分句里找年代，避免后续官职年号干扰
    seg = shizhong_segment(nature)

    # 0) 哀平间
    aiping = parse_aiping(seg) or parse_aiping(nature)
    # 1) 年号
    era_hit = parse_era(seg, dyn) or parse_era(nature, dyn)
    # 2) 帝号
    emp_hit = resolve_emperor(seg, dyn) or resolve_emperor(nature, dyn)
    # 3) 年龄 + 生年
    age_hit = parse_age_term(seg, by) or parse_age_term(nature, by)

    term_start = term_end = None
    term_label = ""
    era_year = None
    source = ""

    if era_hit:
        era_year, term_label, term_end = era_hit
        term_start = era_year
        source = "era"
    elif age_hit:
        era_year, term_label = age_hit
        term_start = term_end = era_year
        source = "age"
    elif aiping:
        term_start, term_end, term_label = aiping
        source = "reign"
    elif emp_hit:
        term_start, term_end, term_label, kind = emp_hit
        source = "reign"
        # 即位/崩时是点，不是段
        if kind in ("accession", "demise"):
            term_end = term_start
        elif kind == "reign" and re.search(re.escape(term_label[:2]) + r"初", seg + nature):
            # 「昭帝初」→ 在位前段
            term_end = term_start + max(1, (term_end - term_start) // 3)
            term_label = term_label.replace("时", "初")
    elif "更始" in seg or ("更始" in nature and "侍中" in nature):
        term_start, term_end, term_label = 23, 25, "更始"
        source = "reign"
    elif nature and "曹爽" in nature:
        term_start, term_end, term_label = 239, 249, "曹爽秉政"
        source = "reign"

    # 精度：有生卒→exact；有年号/年龄→era；有帝号→reign；否则 dynasty
    has_bd = by is not None or dy is not None
    if source in ("era", "age"):
        precision = "era"
    elif source == "reign":
        precision = "reign"
    elif has_bd:
        precision = "exact"
    else:
        precision = "dynasty"

    life = None
    if by is not None and dy is not None:
        life = [min(by, dy), max(by, dy)]
    elif by is not None:
        life = [by, by]
    elif dy is not None:
        life = [dy, dy]

    term = None
    if term_start is not None:
        term = [term_start, term_end if term_end is not None else term_start]

    # 仅生卒、无侍中年：不把朝代窗口当 term
    return {
        "id": c["id"],
        "name": name,
        "style": c["style_name"],
        "dynasty": dyn,
        "category": c["category"],
        "nature": nature,
        "birth": c["birth"],
        "death": c["death"],
        "birth_year": by,
        "death_year": dy,
        "precision": precision,
        "life": life,
        "term": term,
        "term_label": term_label,
        "era_year": era_year,
        "source": source,
        "status": c["status"],
    }


def sort_key(it: dict):
    if it.get("era_year") is not None:
        return (0, it["era_year"], it["name"])
    if it.get("term"):
        return (1, (it["term"][0] + it["term"][1]) / 2, it["name"])
    if it.get("death_year") is not None:
        return (2, it["death_year"], it["name"])
    if it.get("birth_year") is not None:
        return (3, it["birth_year"], it["name"])
    win = DYN_WINDOW.get(it["dynasty"], (0, 0))
    return (4, win[0], it["name"])


def main() -> None:
    cards = []
    for p in sorted(CARDS.glob("*.md")):
        c = parse_card(p)
        if not c or not c["name"]:
            continue
        # 制度条目不是人物，不进时间轴
        if c.get("category") == "制度" or "佚名" in c["name"]:
            continue
        cards.append(classify(c))

    plotted = [c for c in cards if c["precision"] in ("exact", "era", "reign")]
    aggregated = [c for c in cards if c["precision"] == "dynasty"]
    plotted.sort(key=sort_key)

    # 朝代聚合：仅朝代者的数量 + 窗口
    agg_map: dict[str, dict] = {}
    for c in aggregated:
        dyn = c["dynasty"] or "未标"
        if dyn not in agg_map:
            win = DYN_WINDOW.get(dyn)
            agg_map[dyn] = {
                "dynasty": dyn,
                "count": 0,
                "start": win[0] if win else None,
                "end": win[1] if win else None,
                "names": [],
            }
        agg_map[dyn]["count"] += 1
        agg_map[dyn]["names"].append(c["name"])
    aggregates = sorted(agg_map.values(), key=lambda x: -(x["count"] or 0))

    # 帝号参考带（两汉主要皇帝，供刻度）
    emperor_bands = []
    for label, (dyn, y0, y1) in [
        ("武帝", EMPERORS_CANON["武帝"]),
        ("昭帝", EMPERORS_CANON["昭帝"]),
        ("宣帝", EMPERORS_CANON["宣帝"]),
        ("成帝", EMPERORS_CANON["成帝"]),
        ("光武", EMPERORS_CANON["光武"]),
        ("明帝", EMPERORS_CANON["東漢明帝"]),
        ("章帝", EMPERORS_CANON["章帝"]),
        ("和帝", EMPERORS_CANON["和帝"]),
        ("安帝", EMPERORS_CANON["安帝"]),
        ("顺帝", EMPERORS_CANON["顺帝"]),
        ("桓帝", EMPERORS_CANON["桓帝"]),
        ("灵帝", EMPERORS_CANON["灵帝"]),
        ("献帝", EMPERORS_CANON["献帝"]),
    ]:
        emperor_bands.append({"name": label, "dynasty": dyn, "start": y0, "end": y1})

    # items：前端只画 plotted；aggregated 进 aggregates
    items = []
    for c in plotted:
        items.append(
            {
                "id": c["id"],
                "name": c["name"],
                "style": c["style"],
                "dynasty": c["dynasty"],
                "category": c["category"],
                "nature": c["nature"],
                "birth": c["birth"],
                "death": c["death"],
                "precision": c["precision"],
                "life": c["life"],
                "term": c["term"],
                "term_label": c["term_label"],
                "era_year": c["era_year"],
                "source": c["source"],
            }
        )

    # 精度统计
    stats = {
        "exact": sum(1 for c in cards if c["precision"] == "exact"),
        "era": sum(1 for c in cards if c["precision"] == "era"),
        "reign": sum(1 for c in cards if c["precision"] == "reign"),
        "dynasty": sum(1 for c in cards if c["precision"] == "dynasty"),
    }

    payload = {
        "meta": {
            "count": len(cards),
            "plotted": len(items),
            "aggregated": len(aggregated),
            "stats": stats,
            "range": [-210, 290],
            "primary": "#7E0C6E",
            "note": "exact=生卒可考；era=年号可定；reign=帝号在位期；dynasty=仅朝代（不画个人条）",
        },
        "bands": BANDS,
        "emperors": emperor_bands,
        "aggregates": aggregates,
        "items": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=None), encoding="utf-8")
    print(
        f"timeline items plotted={len(items)} aggregated={len(aggregated)} "
        f"stats={stats} -> {OUT}"
    )

    # 回写 DB：只更新年代列，不覆盖 nature
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(person)")
    have = {r[1] for r in cur.fetchall()}
    for col, typ in [
        ("dynasty_primary", "TEXT"),
        ("birth_year", "INTEGER"),
        ("death_year", "INTEGER"),
        ("year_precision", "TEXT"),
        ("term_start_year", "INTEGER"),
        ("term_end_year", "INTEGER"),
        ("term_label", "TEXT"),
    ]:
        if col not in have:
            cur.execute(f"ALTER TABLE person ADD COLUMN {col} {typ}")
    for c in cards:
        cur.execute(
            """UPDATE person SET dynasty_primary=?, birth_year=?, death_year=?,
               year_precision=?, term_start_year=?, term_end_year=?, term_label=?
               WHERE id=?""",
            (
                c["dynasty"],
                c["birth_year"],
                c["death_year"],
                c["precision"],
                c["term"][0] if c["term"] else None,
                c["term"][1] if c["term"] else None,
                c["term_label"] or None,
                c["id"],
            ),
        )
    # term.start_year：仅当年号可定
    cur.execute("PRAGMA table_info(shizhong_term)")
    thave = {r[1] for r in cur.fetchall()}
    if "start_year" not in thave:
        cur.execute("ALTER TABLE shizhong_term ADD COLUMN start_year INTEGER")
    for c in cards:
        if c["era_year"] is not None:
            cur.execute(
                "UPDATE shizhong_term SET start_year=? WHERE person_id=?",
                (c["era_year"], c["id"]),
            )
    con.commit()
    con.close()
    print("db person/term year columns updated")


if __name__ == "__main__":
    main()
