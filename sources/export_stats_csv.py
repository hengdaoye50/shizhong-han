"""导出统计友好 CSV 到 data/exports/。

- persons_wide.csv     一人一行
- terms_long.csv       任职事件（long）
- relations_edges.csv  边表
- persons_attrs.csv    节点属性（网络软件）
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "shizhong.db"
OUT = ROOT / "data" / "exports"


def dump(cur: sqlite3.Cursor, sql: str, name: str) -> None:
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    path = OUT / name
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows, {len(cols)} cols")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    cur = con.cursor()

    dump(
        cur,
        """
        SELECT
          id, name, style_name, dynasty, dynasty_primary, category,
          origin, birth, death, birth_year, death_year, year_precision,
          is_外戚, is_士人, is_降人, is_佞幸, is_宦官, is_勋贵,
          n_terms, n_sources, status
        FROM person
        ORDER BY dynasty_primary, name
        """,
        "persons_wide.csv",
    )

    dump(
        cur,
        """
        SELECT
          t.id AS term_id, t.person_id, p.name, p.dynasty_primary,
          t.start_ym, t.end_ym, t.start_year, t.end_year,
          t.nature, t.nature_primary, t.evidence,
          s.book, s.juan, substr(s.quote,1,200) AS quote_head
        FROM shizhong_term t
        JOIN person p ON p.id = t.person_id
        LEFT JOIN source s ON s.id = t.source_id
        ORDER BY p.dynasty_primary, p.name, t.id
        """,
        "terms_long.csv",
    )

    dump(
        cur,
        """
        SELECT
          id, from_id, from_name, to_id, to_name,
          rel_type, rel_primary,
          is_kinship, is_patron, is_conflict, note, status
        FROM relation
        ORDER BY rel_primary, from_name, to_name
        """,
        "relations_edges.csv",
    )

    dump(
        cur,
        """
        SELECT
          id, name, dynasty_primary, category,
          is_外戚, is_士人, is_降人, is_佞幸, is_宦官, is_勋贵,
          n_terms, n_sources, status
        FROM person
        """,
        "persons_attrs.csv",
    )

    # 简易描述统计
    dump(
        cur,
        """
        SELECT dynasty_primary, COUNT(*) AS n_person,
               SUM(is_外戚) AS n_外戚, SUM(is_士人) AS n_士人,
               SUM(n_terms) AS n_terms
        FROM person GROUP BY dynasty_primary ORDER BY n_person DESC
        """,
        "stats_by_dynasty.csv",
    )

    dump(
        cur,
        """
        SELECT rel_primary, COUNT(*) AS n_edge,
               SUM(is_kinship) AS kin, SUM(is_patron) AS patron, SUM(is_conflict) AS conf
        FROM relation GROUP BY rel_primary ORDER BY n_edge DESC
        """,
        "stats_by_reltype.csv",
    )

    con.close()
    print("exports ->", OUT)


if __name__ == "__main__":
    main()
