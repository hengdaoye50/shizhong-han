"""导出 Web UI 用 JSON：data/shizhong.json"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import t2s

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "shizhong.db"
OUT = ROOT / "shizhongdata" / "data" / "shizhong.json"

# 展示用朝代归并（筛选与角标）；完整标签保留在 dynasty_full
DYN_GROUP = {
    "西汉": "西汉",
    "西漢": "西汉",
    "新": "新",
    "更始": "更始",
    "东汉": "东汉",
    "東漢": "东汉",
    "汉魏之际": "汉魏之际",
    "漢魏之際": "汉魏之际",
    "魏": "魏",
    "蜀汉": "蜀汉",
    "蜀漢": "蜀汉",
    "吴": "吴",
    "吳": "吴",
    "晋": "晋",
    "晉": "晋",
    "西汉_新": "西汉",
    "西漢_新": "西汉",
    "西汉_东汉": "东汉",
    "西漢_東漢": "东汉",
    "更始_东汉": "东汉",
    "更始_東漢": "东汉",
    "蜀汉_魏": "汉魏之际",
    "蜀漢_魏": "汉魏之际",
    "魏_晋": "晋",
    "魏_晉": "晋",
    "两汉": "东汉",
    "兩漢": "东汉",
}


def dyn_group(label: str) -> str:
    s = t2s(label or "").strip()
    if s in DYN_GROUP:
        return DYN_GROUP[s]
    # 复合朝代：含东汉优先东汉，含西汉优先西汉，含晋→晋
    if "东汉" in s:
        return "东汉"
    if "西汉" in s:
        return "西汉"
    if "晋" in s:
        return "晋"
    if "汉魏" in s:
        return "汉魏之际"
    return s or "未标"


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
           FROM person
           WHERE IFNULL(category,'') <> '制度'
             AND name NOT LIKE '%制度%'
           ORDER BY dynasty_primary, name"""
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
        # term 再按 nature 去重（双保险）
        seen_nat = set()
        terms_u = []
        for t in terms:
            k = (t.get("nature") or "").strip()
            if k and k in seen_nat:
                continue
            seen_nat.add(k)
            terms_u.append(t)
        terms = terms_u

        sources = []
        # 1) term.source_id
        sources.extend(
            dict(r)
            for r in cur.execute(
                """SELECT s.book, s.juan, s.quote
                   FROM source s JOIN shizhong_term t ON t.source_id=s.id
                   WHERE t.person_id=?""",
                (p["id"],),
            )
        )
        # 2) source.path 指向该人卡片（补全卡内多条原典）
        name = p["name"] or ""
        dyn = (p["dynasty"] or p["dynasty_primary"] or "").strip()
        path_like = f"{name}_%"
        sources.extend(
            dict(r)
            for r in cur.execute(
                """SELECT book, juan, quote FROM source
                   WHERE path LIKE ? LIMIT 20""",
                (path_like,),
            )
        )
        if dyn:
            sources.extend(
                dict(r)
                for r in cur.execute(
                    """SELECT book, juan, quote FROM source
                       WHERE path LIKE ? LIMIT 20""",
                    (f"{name}_{dyn}%",),
                )
            )

        seen = set()
        src_u = []
        for s in sources:
            q = (s.get("quote") or "").strip()
            k = re.sub(r"\s+", "", q).replace("「", "").replace("」", "")
            if not q or (k and k in seen):
                continue
            seen.add(k)
            src_u.append(s)
        sources = src_u[:16]

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
                "dynasty": dyn_group(p["dynasty_primary"] or p["dynasty"] or ""),
                "dynasty_full": t2s(p["dynasty_primary"] or p["dynasty"] or ""),
                "dynasty_raw": t2s(p["dynasty"] or ""),
                "category": p["category"] or "",
                "origin": p["origin"] or "",
                "birth": p["birth"] or "",
                "death": p["death"] or "",
                "birth_year": p["birth_year"],
                "death_year": p["death_year"],
                # 以实际条数为准，库列可能未回填
                "n_terms": len(terms),
                "n_sources": len(sources),
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
                "sources": sources,
                "relations_out": rels_out,
                "relations_in": rels_in,
            }
        )

    # stats — 按归并后的朝代组
    dyn_counts = {}
    for per in persons:
        g = per["dynasty"] or "?"
        dyn_counts[g] = dyn_counts.get(g, 0) + 1
    # 固定顺序
    order = ["西汉", "新", "更始", "东汉", "汉魏之际", "魏", "蜀汉", "吴", "晋"]
    dyn_counts = {k: dyn_counts[k] for k in order if k in dyn_counts}
    dyn_counts.update({k: v for k, v in dyn_counts.items() if k not in order})
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
            "updated": "2026-09-15",
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
