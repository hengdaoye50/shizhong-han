"""为 SQLite 增加统计友好列，并做基础归一与计数回填。

不改卡片 Markdown；只改库与导出。
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "shizhong.db"

# 年号粗对照（仅用于可算年份；填不上保持 NULL）
# 公元 = 起始年 + (元年-1)；此处只处理卡片里已写死的公元或明确年
YEAR_IN_TEXT = re.compile(r"(前)?(\d{1,4})")


def add_cols(cur: sqlite3.Cursor, table: str, cols: list[tuple[str, str]]) -> None:
    cur.execute(f"PRAGMA table_info({table})")
    have = {r[1] for r in cur.fetchall()}
    for name, typ in cols:
        if name not in have:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
            print(f"add {table}.{name}")


def parse_year(s: str) -> tuple[int | None, str]:
    if not s:
        return None, "unknown"
    s = s.strip()
    if s in ("阙", "待填", "—", "-", "未就任"):
        return None, "unknown"
    # 前140 / 前1
    m = re.match(r"前(\d+)", s)
    if m:
        return -int(m.group(1)), "approx"
    m = re.match(r"^(\d{1,4})$", s)
    if m:
        return int(m.group(1)), "approx"
    # 前23
    m = re.match(r"前\s*(\d+)", s)
    if m:
        return -int(m.group(1)), "approx"
    # 92 / 200 等
    m = re.search(r"(前)?(\d{3,4})", s)
    if m:
        y = int(m.group(2))
        if m.group(1):
            y = -y
        return y, "approx"
    return None, "unknown"


DYN_PRIMARY = {
    "西漢": "西漢",
    "東漢": "東漢",
    "新": "新",
    "更始": "更始",
    "魏": "魏",
    "蜀漢": "蜀漢",
    "吳": "吳",
    "晉": "晉",
    "漢魏之際": "漢魏之際",
    "魏_晉": "魏",
    "西漢_新": "西漢",
    "更始_東漢": "更始",
    "西漢_東漢": "西漢",
    "蜀漢_魏": "蜀漢",
    "兩漢": "兩漢",
    "两汉": "兩漢",
}

TAGS = {
    "外戚": ["外戚"],
    "士人": ["士人", "儒"],
    "降人": ["降人"],
    "佞幸": ["佞幸"],
    "宦官": ["宦官"],
    "勋贵": ["勋贵", "云台"],
}


def main() -> None:
    con = sqlite3.connect(DB)
    cur = con.cursor()

    add_cols(
        cur,
        "person",
        [
            ("dynasty_primary", "TEXT"),
            ("birth_year", "INTEGER"),
            ("death_year", "INTEGER"),
            ("year_precision", "TEXT"),
            ("is_外戚", "INTEGER DEFAULT 0"),
            ("is_士人", "INTEGER DEFAULT 0"),
            ("is_降人", "INTEGER DEFAULT 0"),
            ("is_佞幸", "INTEGER DEFAULT 0"),
            ("is_宦官", "INTEGER DEFAULT 0"),
            ("is_勋贵", "INTEGER DEFAULT 0"),
            ("n_terms", "INTEGER DEFAULT 0"),
            ("n_sources", "INTEGER DEFAULT 0"),
        ],
    )
    add_cols(
        cur,
        "shizhong_term",
        [
            ("start_year", "INTEGER"),
            ("end_year", "INTEGER"),
            ("nature_primary", "TEXT"),
            ("n_quotes", "INTEGER DEFAULT 0"),
        ],
    )
    add_cols(
        cur,
        "relation",
        [
            ("rel_primary", "TEXT"),
            ("is_kinship", "INTEGER DEFAULT 0"),
            ("is_patron", "INTEGER DEFAULT 0"),
            ("is_conflict", "INTEGER DEFAULT 0"),
        ],
    )

    # person 回填
    cur.execute("SELECT id, dynasty, category, birth, death FROM person")
    persons = cur.fetchall()
    for pid, dyn, cat, birth, death in persons:
        dp = DYN_PRIMARY.get((dyn or "").strip(), dyn or "")
        by, bp = parse_year(birth or "")
        dy, dp2 = parse_year(death or "")
        prec = "unknown"
        if by is not None or dy is not None:
            prec = "approx"
        flags = {}
        blob = (cat or "") + " " + (dyn or "")
        for k, keys in TAGS.items():
            flags[f"is_{k}"] = 1 if any(x in blob for x in keys) else 0
        cur.execute(
            """UPDATE person SET dynasty_primary=?, birth_year=?, death_year=?, year_precision=?,
               is_外戚=?, is_士人=?, is_降人=?, is_佞幸=?, is_宦官=?, is_勋贵=?
               WHERE id=?""",
            (
                dp, by, dy, prec,
                flags["is_外戚"], flags["is_士人"], flags["is_降人"],
                flags["is_佞幸"], flags["is_宦官"], flags["is_勋贵"],
                pid,
            ),
        )
    # 计数
    cur.execute(
        """UPDATE person SET
        n_terms = (SELECT COUNT(*) FROM shizhong_term t WHERE t.person_id = person.id),
        n_sources = (SELECT COUNT(DISTINCT s.id) FROM source s
                     JOIN shizhong_term t ON t.source_id = s.id
                     WHERE t.person_id = person.id)"""
    )

    # term：nature 归一 + 年份（从 nature/空白处抓公元很少；保持 NULL 除非 start_ym 有数字）
    cur.execute("SELECT id, start_ym, end_ym, nature FROM shizhong_term")
    for tid, s, e, nat in cur:
        nat = nat or ""
        if "加官" in nat:
            np = "加官"
        elif "正职" in nat or "正職" in nat:
            np = "正職"
        elif "复合" in nat or "僕射" in nat or "仆射" in nat:
            np = "复合官"
        else:
            np = "其他"
        sy, _ = parse_year(s or "")
        ey, _ = parse_year(e or "")
        cur.execute(
            "UPDATE shizhong_term SET nature_primary=?, start_year=?, end_year=? WHERE id=?",
            (np, sy, ey, tid),
        )

    # relation rel_primary
    KIN = {"父", "母", "子", "女", "兄弟", "从父", "从子", "祖", "曾祖", "高祖", "夫妻", "姻亲", "外戚", "先祖", "宗族"}
    PAT = {"举主", "府主", "师", "同门"}
    CONF = {"政敌", "同谋"}
    cur.execute("SELECT id, rel_type FROM relation")
    for rid, rt in cur.fetchall():
        rp = rt or "其他"
        cur.execute(
            """UPDATE relation SET rel_primary=?, is_kinship=?, is_patron=?, is_conflict=?
               WHERE id=?""",
            (
                rp,
                1 if rp in KIN else 0,
                1 if rp in PAT else 0,
                1 if rp in CONF else 0,
                rid,
            ),
        )

    con.commit()
    cur.execute("SELECT COUNT(*) FROM person WHERE birth_year IS NOT NULL OR death_year IS NOT NULL")
    print("person with any year", cur.fetchone()[0])
    cur.execute("SELECT dynasty_primary, COUNT(*) FROM person GROUP BY dynasty_primary ORDER BY 2 DESC")
    print("dynasty_primary:")
    for a, b in cur.fetchall():
        print(f"  {b:4d} {a}")
    cur.execute("SELECT nature_primary, COUNT(*) FROM shizhong_term GROUP BY nature_primary")
    print("nature:", cur.fetchall())
    con.close()
    print("schema upgrade done ->", DB)


if __name__ == "__main__":
    main()
