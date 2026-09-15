"""导出 Web UI 用 JSON：data/shizhong.json"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "shizhong.db"
OUT = ROOT / "shizhongdata" / "data" / "shizhong.json"


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    persons = []
    persons_rows = list(
        cur.execute(
            """SELECT id, name, style_name, dynasty, dynasty_primary, category,
                  origin, birth, death, birth_year, death_year,
                  is_外戚, is_士人, is_降人, is_佞幸, is_宦官, is_勋贵,
                  n_terms, n_sources, status, notes
           FROM person ORDER BY dynasty_primary, name"""
        )
    )
    for p in persons_rows:
        terms = [
            dict(r)
            for r in cur.execute(
                """SELECT nature, nature_primary, start_ym, end_ym, evidence
                   FROM shizhong_term WHERE person_id=?""",
                (p["id"],),
            )
        ]
        sources = [
            dict(r)
            for r in cur.execute(
                """SELECT s.book, s.juan, s.quote
                   FROM source s JOIN shizhong_term t ON t.source_id=s.id
                   WHERE t.person_id=? LIMIT 8""",
                (p["id"],),
            )
        ]
        # unique sources by quote
        seen = set()
        src_u = []
        for s in sources:
            k = (s["book"], s["juan"], (s["quote"] or "")[:40])
            if k in seen:
                continue
            seen.add(k)
            src_u.append(s)

        rels_out = [
            dict(r)
            for r in cur.execute(
                """SELECT to_name, rel_primary, note FROM relation
                   WHERE from_name=? LIMIT 20""",
                (p["name"],),
            )
        ]
        rels_in = [
            dict(r)
            for r in cur.execute(
                """SELECT from_name AS to_name, rel_primary, note FROM relation
                   WHERE to_name=? LIMIT 12""",
                (p["name"],),
            )
        ]

        persons.append(
            {
                "id": p["id"],
                "name": p["name"],
                "style_name": p["style_name"] or "",
                "dynasty": p["dynasty_primary"] or p["dynasty"] or "",
                "dynasty_raw": p["dynasty"] or "",
                "category": p["category"] or "",
                "origin": p["origin"] or "",
                "birth": p["birth"] or "",
                "death": p["death"] or "",
                "birth_year": p["birth_year"],
                "death_year": p["death_year"],
                "n_terms": p["n_terms"] or 0,
                "n_sources": p["n_sources"] or 0,
                "status": p["status"] or "",
                "tags": [
                    t
                    for t, v in [
                        ("外戚", p["is_外戚"]),
                        ("士人", p["is_士人"]),
                        ("降人", p["is_降人"]),
                        ("佞幸", p["is_佞幸"]),
                        ("宦官", p["is_宦官"]),
                        ("勋贵", p["is_勋贵"]),
                    ]
                    if v
                ],
                "terms": terms,
                "sources": src_u,
                "relations_out": rels_out,
                "relations_in": rels_in,
            }
        )

    # stats
    dyn_counts = {}
    for r in cur.execute(
        "SELECT dynasty_primary, COUNT(*) c FROM person GROUP BY dynasty_primary"
    ):
        dyn_counts[r["dynasty_primary"] or "?"] = r["c"]
    rel_counts = {}
    for r in cur.execute(
        "SELECT rel_primary, COUNT(*) c FROM relation GROUP BY rel_primary ORDER BY c DESC"
    ):
        rel_counts[r["rel_primary"] or "?"] = r["c"]

    # 前端不展示审校状态
    for p in persons:
        p.pop("status", None)

    payload = {
        "meta": {
            "title": "两汉侍中数据库",
            "subtitle": "Shizhong of the Han",
            "person_count": len(persons),
            "relation_count": sum(rel_counts.values()),
            "source_count": cur.execute("SELECT COUNT(*) FROM source").fetchone()[0],
            "updated": "2026-09-13",
            "primary": "#7E0C6E",
        },
        "dynasty_counts": dyn_counts,
        "relation_counts": rel_counts,
        "persons": persons,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("persons", len(persons), "->", OUT, "bytes", OUT.stat().st_size)
    con.close()


if __name__ == "__main__":
    main()
