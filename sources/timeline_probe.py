"""统计可定位年代的数据，供时间轴使用。"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "shizhong.db"

# 常见年号 → 大致起始公元（粗表，用于 timeline 定位）
ERA = {
    "建武": 25, "永平": 58, "建初": 76, "元和": 84, "章和": 87,
    "永元": 89, "元兴": 105, "延平": 106, "永初": 107, "元初": 114,
    "永宁": 120, "建光": 121, "延光": 122, "永建": 126, "阳嘉": 132,
    "永和": 136, "汉安": 142, "建康": 144, "永憙": 145, "本初": 146,
    "建和": 147, "和平": 150, "元嘉": 151, "永兴": 153, "永寿": 155,
    "延熹": 158, "永康": 167, "建宁": 168, "熹平": 172, "光和": 178,
    "中平": 184, "初平": 190, "兴平": 194, "建安": 196, "延康": 220,
    "黄初": 220, "太和": 227, "青龙": 233, "景初": 237, "正始": 240,
    "嘉平": 249, "正元": 254, "甘露": 256, "景元": 260, "咸熙": 264,
    "泰始": 265, "建兴": 223, "延熙": 238, "景耀": 258, "炎兴": 263,
    "黄武": 222, "黄龙": 229, "嘉禾": 232, "赤乌": 238, "太元": 251,
    "神凤": 252, "建兴": 252, "五凤": 254, "太平": 256, "永安": 258,
    "元兴": 264, "甘露": 265, "宝鼎": 266, "建衡": 269, "凤凰": 272,
    "天册": 275, "天玺": 276, "天纪": 277,
}


def era_to_year(s: str) -> int | None:
    if not s:
        return None
    # 前\d+
    m = re.match(r"前(\d+)", s.strip())
    if m:
        return -int(m.group(1))
    # 明确公元
    m = re.search(r"(前)?(\d{3,4})", s)
    if m and int(m.group(2)) < 300:
        y = int(m.group(2))
        return -y if m.group(1) else y
    # 年号 + 元年/数字
    for era, y0 in ERA.items():
        if era in s:
            m = re.search(era + r"[一二三四五六七八九十百零〇\d]*", s)
            # 取「元年」或数字
            tail = m.group(0)[len(era):] if m else ""
            n = 1
            if tail:
                cn = {"元": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
                if tail in cn:
                    n = cn[tail]
                elif tail.isdigit():
                    n = int(tail)
                elif "元" in tail:
                    n = 1
            return y0 + n - 1
    return None


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # 从 nature / start_ym 抽年
    rows = list(
        cur.execute(
            """SELECT t.id, t.person_id, p.name, p.dynasty_primary, t.nature, t.start_ym, t.end_ym
               FROM shizhong_term t JOIN person p ON p.id=t.person_id"""
        )
    )
    located = 0
    for r in rows:
        y = era_to_year(r["nature"] or "") or era_to_year(r["start_ym"] or "")
        if y:
            located += 1
    print("terms", len(rows), "located_by_era", located)

    # person-level: use dynasty decade windows if no year
    DYN_WINDOW = {
        "西漢": (-202, 8),
        "新": (9, 23),
        "更始": (23, 25),
        "東漢": (25, 220),
        "漢魏之際": (200, 230),
        "魏": (220, 265),
        "蜀漢": (221, 263),
        "吳": (222, 280),
        "晉": (265, 280),
        "西漢_新": (-202, 23),
        "更始_東漢": (23, 220),
        "西漢_東漢": (-202, 220),
        "兩漢": (-202, 220),
        "蜀漢_魏": (221, 265),
        "魏_晉": (220, 280),
    }
    persons = list(cur.execute("SELECT id, name, dynasty_primary, birth_year, death_year FROM person"))
    n_win = 0
    for p in persons:
        if p["birth_year"] or p["death_year"]:
            n_win += 1
        elif p["dynasty_primary"] in DYN_WINDOW:
            n_win += 1
    print("persons", len(persons), "plottable", n_win)
    con.close()


if __name__ == "__main__":
    main()
