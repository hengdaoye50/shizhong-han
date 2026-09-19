"""把 data/cards/ 中指定人员（或全部缺失 id）增量写入 SQLite。

不重编号、不删既有 relation。仅 INSERT OR REPLACE person，
并为该人删除旧 term/source 后按卡片重建，避免重复 import_pilot 全量副作用。

用法:
  python sources/upsert_cards_to_db.py
  python sources/upsert_cards_to_db.py --names 辛毗,孙资
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import t2s

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

# 本轮拟补审定通过人员（可扩展）
DEFAULT_NAMES = [
    "辛毗",
    "张辟疆",
    "孔安国",
    "卓茂",
    "卫觊",
    "孙资",
    "丁冲",
    "金建",
    "李祯",
    "梁安国",
]


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


def card_for(name: str) -> Path | None:
    hits = [p for p in CARDS.glob("*.md") if p.stem.split("_")[0] == name]
    return hits[0] if hits else None


def upsert_card(cur: sqlite3.Cursor, path: Path) -> str:
    fm = parse_front_matter(path.read_text(encoding="utf-8"))
    pid = fm.get("id") or ""
    name = fm.get("name") or path.stem.split("_")[0]
    if not pid:
        raise SystemExit(f"missing id: {path.name}")
    cur.execute(
        """INSERT OR REPLACE INTO person
           (id,name,style_name,dynasty,category,origin,birth,death,status,notes)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            pid,
            t2s(name),
            t2s(fm.get("style_name", "")),
            t2s(fm.get("dynasty", "")),
            t2s(fm.get("category", "")),
            t2s(fm.get("origin", "")),
            t2s(fm.get("birth", "")),
            t2s(fm.get("death", "")),
            t2s(fm.get("status", "已校")),
            path.name,
        ),
    )
    sids = [
        r[0]
        for r in cur.execute(
            "SELECT id FROM source WHERE path=?", (path.name,)
        )
    ]
    cur.execute("DELETE FROM shizhong_term WHERE person_id=?", (pid,))
    for sid in sids:
        cur.execute("DELETE FROM source WHERE id=?", (sid,))

    terms = fm.get("terms") or []
    if not terms:
        terms = [{"start": "阙", "end": "阙", "nature": "", "evidence": "有明文"}]
    for s in fm.get("sources") or []:
        book = t2s(s.get("book") or "")
        juan = t2s(s.get("juan") or "")
        quote = t2s(s.get("quote") or "")
        if not book or book == "阙":
            continue
        cur.execute(
            "INSERT INTO source (book,juan,quote,path) VALUES (?,?,?,?)",
            (book, juan, quote, path.name),
        )
        sid = cur.lastrowid
        for t in terms:
            cur.execute(
                """INSERT OR IGNORE INTO shizhong_term
                   (person_id,start_ym,end_ym,nature,evidence,source_id)
                   VALUES (?,?,?,?,?,?)""",
                (
                    pid,
                    t2s(t.get("start") or "阙"),
                    t2s(t.get("end") or "阙"),
                    t2s(t.get("nature") or ""),
                    t2s(t.get("evidence") or "有明文"),
                    sid,
                ),
            )
    return f"{pid} {name}"


DEFAULT_RELS = [
    # from, to, type, note
    ("辛毗", "刘放", "同僚", "毗不与往来"),
    ("辛毗", "孙资", "同僚", "毗不与往来"),
    ("辛毗", "刘廙", "同僚", "魏王侍中联名"),
    ("辛毗", "刘晔", "同僚", "联名奏议"),
    ("孙资", "刘放", "同僚", "并典机密"),
    ("卫觊", "王粲", "同僚", "并典制度"),
    ("张辟疆", "张良", "父子", "留侯子"),
    ("张辟疆", "陈平", "同僚", "说平安吕"),
    ("金建", "金日磾", "父子", "日磾两子"),
    ("金建", "金赏", "兄弟", "俱侍中"),
    ("丁冲", "种辑", "同僚", "同封列侯"),
    ("丁冲", "伏完", "同僚", "同封列侯"),
    ("李祯", "李傕", "府主", "州里，素与傕通"),
    ("梁安国", "梁棠", "父子", "棠卒子安国嗣"),
    ("孔安国", "孔臧", "宗族", "臧与子琳书"),
    ("卓茂", "更始帝", "与帝", "侍中祭酒"),
]


def upsert_default_relations(cur: sqlite3.Cursor, name_to_id: dict[str, str]) -> int:
    n = 0
    for from_name, to_name, rel_type, note in DEFAULT_RELS:
        if from_name not in name_to_id:
            continue
        fid = name_to_id[from_name]
        tid = name_to_id.get(to_name, "")
        cur.execute(
            """INSERT INTO relation
               (from_id,from_name,to_id,to_name,rel_type,note,status)
               VALUES (?,?,?,?,?,?,?)""",
            (
                fid,
                t2s(from_name),
                tid,
                t2s(to_name),
                t2s(rel_type),
                t2s(note),
                "已校",
            ),
        )
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", default="", help="逗号分隔；默认本轮拟补名单")
    args = ap.parse_args()
    names = [x.strip() for x in args.names.split(",") if x.strip()] or DEFAULT_NAMES

    if not DB.exists():
        raise SystemExit("run init_db.py first")
    con = sqlite3.connect(DB)
    cur = con.cursor()

    name_to_id: dict[str, str] = {}
    for name in names:
        p = card_for(name)
        if not p:
            print("MISS", name)
            continue
        print("UPSERT", upsert_card(cur, p))
        fm = parse_front_matter(p.read_text(encoding="utf-8"))
        name_to_id[fm.get("name") or name] = fm.get("id") or ""

    # 补关系：仅当两端名在库中可解析时写入 from_id
    id_by_name = {
        r[0]: r[1]
        for r in cur.execute("SELECT name, id FROM person")
    }
    for k, v in list(name_to_id.items()):
        name_to_id[k] = id_by_name.get(k, v)
    n_rel = upsert_default_relations(cur, name_to_id)

    cur.execute(
        """UPDATE person SET
           n_terms = (SELECT COUNT(*) FROM shizhong_term t WHERE t.person_id = person.id),
           n_sources = (
             SELECT COUNT(DISTINCT t.source_id) FROM shizhong_term t
             WHERE t.person_id = person.id AND t.source_id IS NOT NULL
           )"""
    )
    con.commit()
    for t in ("person", "term_placeholder"):
        pass
    cur.execute("SELECT COUNT(*) FROM person")
    print("person", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM shizhong_term")
    print("term", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM source")
    print("source", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM relation")
    print("relation", cur.fetchone()[0], f"(+{n_rel} this run)")
    for name in names:
        row = cur.execute(
            "SELECT id,name,dynasty,status FROM person WHERE name=?",
            (name,),
        ).fetchone()
        print(" ", row)
    con.close()


if __name__ == "__main__":
    main()
