"""把 pilot 卡片 + 关系边 + 已审候选导入 SQLite。

用法:
  python sources/import_pilot.py
"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "shizhong.db"


def parse_front_matter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end]
    data: dict = {"sources": [], "terms": []}
    cur_src = None
    cur_t = None
    section = None
    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        if re.match(r"^sources:\s*$", line):
            section = "sources"
            continue
        if re.match(r"^shizhong_terms:\s*$", line):
            section = "terms"
            continue
        if re.match(r"^[A-Za-z_][\w]*:", line) and not line.startswith(" "):
            section = None
            if cur_src:
                data["sources"].append(cur_src)
                cur_src = None
            if cur_t:
                data["terms"].append(cur_t)
                cur_t = None
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
            continue
        if section == "sources":
            if line.strip().startswith("- book:"):
                if cur_src:
                    data["sources"].append(cur_src)
                cur_src = {
                    "book": line.split(":", 1)[1].strip(),
                    "juan": "",
                    "quote": "",
                }
            elif cur_src is not None and "juan:" in line:
                cur_src["juan"] = line.split(":", 1)[1].strip()
            elif cur_src is not None and "quote:" in line:
                cur_src["quote"] = line.split(":", 1)[1].strip().strip("「」")
        elif section == "terms":
            if line.strip().startswith("- start:"):
                if cur_t:
                    data["terms"].append(cur_t)
                cur_t = {"start": line.split(":", 1)[1].strip()}
            elif cur_t is not None and line.strip().startswith("end:"):
                cur_t["end"] = line.split(":", 1)[1].strip()
            elif cur_t is not None and line.strip().startswith("nature:"):
                cur_t["nature"] = line.split(":", 1)[1].strip()
            elif cur_t is not None and line.strip().startswith("evidence:"):
                cur_t["evidence"] = line.split(":", 1)[1].strip()
    if cur_src:
        data["sources"].append(cur_src)
    if cur_t:
        data["terms"].append(cur_t)
    return data


def main() -> None:
    if not DB.exists():
        raise SystemExit("run init_db.py first")
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # persons from cards
    n_person = n_src = n_term = 0
    for p in sorted((ROOT / "data" / "cards").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm = parse_front_matter(text)
        pid = fm.get("id") or p.stem
        name = fm.get("name") or p.stem.split("_")[0]
        cur.execute(
            """INSERT OR REPLACE INTO person
               (id,name,style_name,dynasty,category,origin,birth,death,status,notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                pid,
                name,
                fm.get("style_name", ""),
                fm.get("dynasty", ""),
                fm.get("category", ""),
                fm.get("origin", ""),
                fm.get("birth", ""),
                fm.get("death", ""),
                fm.get("status", "待审"),
                p.name,
            ),
        )
        n_person += 1
        for s in fm.get("sources") or []:
            if not s.get("book") or s.get("book") == "阙":
                continue
            cur.execute(
                "INSERT INTO source (book,juan,quote,path) VALUES (?,?,?,?)",
                (s.get("book"), s.get("juan"), s.get("quote"), p.name),
            )
            sid = cur.lastrowid
            n_src += 1
            for t in fm.get("terms") or []:
                cur.execute(
                    """INSERT OR IGNORE INTO shizhong_term
                       (person_id,start_ym,end_ym,nature,evidence,source_id)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        pid,
                        t.get("start"),
                        t.get("end"),
                        t.get("nature"),
                        t.get("evidence"),
                        sid,
                    ),
                )
                n_term += 1

    # relations
    rel_path = ROOT / "data" / "db" / "pilot_relations.csv"
    n_rel = 0
    if rel_path.exists():
        with rel_path.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                cur.execute(
                    """INSERT INTO relation
                       (from_id,from_name,to_id,to_name,rel_type,note,status)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        r.get("from_id"),
                        r.get("from_name"),
                        r.get("to_id"),
                        r.get("to_name"),
                        r.get("rel_type"),
                        r.get("note"),
                        r.get("status"),
                    ),
                )
                n_rel += 1

    # candidates (pilot queue only)
    qpath = ROOT / "data" / "candidates" / "pilot_queue.csv"
    n_cand = 0
    if qpath.exists():
        with qpath.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                cur.execute(
                    """INSERT INTO candidate
                       (book,juan,source_kind,source_file,match_type,hint_name,
                        sentence,status,person,role_note,review_note,cand_row,pilot)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        r.get("book"),
                        r.get("juan"),
                        r.get("source_kind"),
                        r.get("source_file"),
                        r.get("match_type"),
                        r.get("hint_name"),
                        r.get("sentence"),
                        r.get("status"),
                        r.get("person"),
                        r.get("role_note"),
                        r.get("review_note"),
                        int(r["cand_row"]) if (r.get("cand_row") or "").isdigit() else None,
                        r.get("pilot"),
                    ),
                )
                n_cand += 1

    con.commit()
    # 简查
    for t in ("person", "source", "shizhong_term", "relation", "candidate"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, cur.fetchone()[0])
    print(
        f"imported person+{n_person} source+{n_src} term+{n_term} rel+{n_rel} cand+{n_cand}"
    )
    con.close()


if __name__ == "__main__":
    main()
