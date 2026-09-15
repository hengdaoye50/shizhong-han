"""清理：移除制度卡；卡片与库内任职/引文去重；全文转简体。

不改动生平独立存储（person_bio / data/bio）。
"""

from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import norm_quote, t2s

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

SKIP_NAMES = ("佚名侍中（禁中出入制度）",)


def parse_frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return None, text
    return m.group(1), m.group(2)


def rewrite_card(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(raw)
    if fm is None:
        return {"file": path.name, "skipped": True}

    name_m = re.search(r"^name:\s*(.*)$", fm, re.M)
    name = name_m.group(1).strip() if name_m else ""
    if name in SKIP_NAMES or "制度" in path.name or "佚名" in path.name:
        return {"file": path.name, "remove": True, "name": name}

    changed = False
    fm2 = t2s(fm)

    # sources 块：按行解析，按简体 quote 去重，整块重建
    m = re.search(r"sources:\n((?:[ \t].*\n|\n)*)", fm2)
    if m:
        block = m.group(1)
        entries = []
        cur_e: dict | None = None
        for ln in block.splitlines():
            if not ln.strip():
                continue
            if re.match(r"^\s*-\s+book:", ln):
                if cur_e:
                    entries.append(cur_e)
                cur_e = {"book": re.sub(r".*book:\s*", "", ln).strip(), "juan": "", "quote": ""}
            elif cur_e is not None and re.match(r"^\s+juan:", ln):
                cur_e["juan"] = re.sub(r".*juan:\s*", "", ln).strip()
            elif cur_e is not None and re.match(r"^\s+quote:", ln):
                # 同一条目多 quote：各拆一条
                q = re.sub(r".*quote:\s*", "", ln).strip()
                if cur_e.get("quote"):
                    entries.append(cur_e)
                    cur_e = {"book": cur_e["book"], "juan": cur_e["juan"], "quote": q}
                else:
                    cur_e["quote"] = q
        if cur_e:
            entries.append(cur_e)

        seen = set()
        kept = []
        for e in entries:
            key = norm_quote(e.get("quote") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            kept.append(e)
        new_block = "sources:\n"
        for e in kept:
            new_block += (
                f"  - book: {e['book']}\n    juan: {e['juan']}\n    quote: {e['quote']}\n"
            )
        fm2 = fm2[: m.start()] + new_block + fm2[m.end() :]
        if len(kept) != len(entries):
            changed = True

    # shizhong_terms: 同一 nature 只留第一条
    tb = re.search(r"shizhong_terms:\n((?:  - .*\n(?:    .*\n)*)+)", fm2)
    if tb:
        lines = tb.group(1).splitlines(True)
        items: list[list[str]] = []
        cur: list[str] = []
        for ln in lines:
            if ln.startswith("  - "):
                if cur:
                    items.append(cur)
                cur = [ln]
            else:
                cur.append(ln)
        if cur:
            items.append(cur)
        seen_n: set[str] = set()
        kept_items = []
        for it in items:
            nat_m = re.search(r"nature:\s*(.*)", "".join(it))
            nat = (nat_m.group(1).strip() if nat_m else "")
            if nat and nat in seen_n:
                changed = True
                continue
            seen_n.add(nat)
            kept_items.append(it)
        if len(kept_items) != len(items):
            changed = True
        new_tb = "shizhong_terms:\n" + "".join("".join(x) for x in kept_items)
        fm2 = fm2[: tb.start()] + new_tb + fm2[tb.end() :]

    body2 = t2s(body)
    if body2 != body or fm2 != fm:
        changed = True

    new_raw = f"---\n{fm2}\n---\n{body2}"
    if not new_raw.endswith("\n"):
        new_raw += "\n"
    if changed:
        path.write_text(new_raw, encoding="utf-8")
        return {"file": path.name, "updated": True, "name": name}
    return {"file": path.name, "ok": True, "name": name}


def db_cleanup() -> dict:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    stats = {
        "removed_persons": 0,
        "terms_deleted": 0,
        "sources_deleted": 0,
        "persons_t2s": 0,
    }

    # 1) 删制度卡及其 term/source/relation
    for pid, pname in list(
        cur.execute(
            "SELECT id, name FROM person WHERE category='制度' OR name LIKE '%禁中出入制度%'"
        )
    ):
        sids = [
            r[0]
            for r in cur.execute(
                "SELECT source_id FROM shizhong_term WHERE person_id=?", (pid,)
            )
        ]
        cur.execute("DELETE FROM shizhong_term WHERE person_id=?", (pid,))
        for sid in sids:
            if sid is not None:
                cur.execute("DELETE FROM source WHERE id=?", (sid,))
        cur.execute(
            "DELETE FROM relation WHERE from_name=? OR to_name=?", (pname, pname)
        )
        cur.execute("DELETE FROM person WHERE id=?", (pid,))
        stats["removed_persons"] += 1
        print("db removed person", pid, pname)

    # 2) 显示字段转简体
    for pid, name, style, dynasty, cat, origin, birth, death in list(
        cur.execute(
            "SELECT id, name, style_name, dynasty, category, origin, birth, death FROM person"
        )
    ):
        cur.execute(
            "UPDATE person SET name=?, style_name=?, dynasty=?, category=?, origin=?, birth=?, death=? WHERE id=?",
            (
                t2s(name or ""),
                t2s(style or ""),
                t2s(dynasty or ""),
                t2s(cat or ""),
                t2s(origin or ""),
                t2s(birth or ""),
                t2s(death or ""),
                pid,
            ),
        )
        stats["persons_t2s"] += 1

    for tid, nature, ev in list(
        cur.execute("SELECT id, nature, evidence FROM shizhong_term")
    ):
        cur.execute(
            "UPDATE shizhong_term SET nature=?, evidence=? WHERE id=?",
            (t2s(nature or ""), t2s(ev or ""), tid),
        )

    for sid, book, juan, quote, path in list(
        cur.execute("SELECT id, book, juan, quote, path FROM source")
    ):
        cur.execute(
            "UPDATE source SET book=?, juan=?, quote=?, path=? WHERE id=?",
            (
                t2s(book or ""),
                t2s(juan or ""),
                t2s(quote or ""),
                t2s(path or ""),
                sid,
            ),
        )

    # relation 人名同步简体（与 person.name 对齐）
    for rid, fn, tn, note, rel in list(
        cur.execute("SELECT id, from_name, to_name, note, rel_primary FROM relation")
    ):
        cur.execute(
            "UPDATE relation SET from_name=?, to_name=?, note=?, rel_primary=? WHERE id=?",
            (
                t2s(fn or ""),
                t2s(tn or ""),
                t2s(note or ""),
                t2s(rel or ""),
                rid,
            ),
        )

    # 3) 残留制度 source
    cur.execute(
        "DELETE FROM source WHERE path LIKE ? OR path LIKE ?",
        ("%制度%", "%佚名%"),
    )
    stats["sources_deleted"] += cur.rowcount or 0

    # 4) term 按 person+nature 归一去重
    rows = list(cur.execute("SELECT id, person_id, nature FROM shizhong_term ORDER BY id"))
    seen: set = set()
    del_ids = []
    for tid, pid, nature in rows:
        key = (pid, norm_quote(nature or "") or (nature or "").strip())
        if key in seen:
            del_ids.append(tid)
        else:
            seen.add(key)
    for tid in del_ids:
        cur.execute("DELETE FROM shizhong_term WHERE id=?", (tid,))
    stats["terms_deleted"] = len(del_ids)

    # 5) source 按 (书, 简体quote) 去重
    rows = list(cur.execute("SELECT id, book, juan, quote FROM source ORDER BY id"))
    seen = set()
    del_sids = []
    for sid, book, juan, quote in rows:
        key = (t2s(book or ""), norm_quote(quote or ""))
        if not key[1]:
            continue
        if key in seen:
            del_sids.append(sid)
        else:
            seen.add(key)
    for sid in del_sids:
        cur.execute(
            "UPDATE shizhong_term SET source_id=NULL WHERE source_id=?", (sid,)
        )
        cur.execute("DELETE FROM source WHERE id=?", (sid,))
    stats["sources_deleted"] += len(del_sids)

    # 6) 回填计数
    cur.execute(
        """UPDATE person SET
           n_terms = (SELECT COUNT(*) FROM shizhong_term t WHERE t.person_id = person.id),
           n_sources = (
             SELECT COUNT(DISTINCT t.source_id) FROM shizhong_term t
             WHERE t.person_id = person.id AND t.source_id IS NOT NULL
           )"""
    )

    con.commit()
    con.close()
    return stats


def main() -> None:
    removed = updated = 0
    for p in sorted(CARDS.glob("*.md")):
        r = rewrite_card(p)
        if r.get("remove"):
            p.unlink(missing_ok=True)
            removed += 1
            print("removed card", p.name)
        elif r.get("updated"):
            updated += 1
    print(f"cards removed={removed} updated={updated}")
    print("db", db_cleanup())


if __name__ == "__main__":
    main()
