"""按 persons_evidence.csv 批量生成全量骨架卡，并导入 SQLite。

用法:
  python sources/build_full_cards.py
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

# 已有详卡（跳过覆盖）
KEEP_DETAIL = {
    "金日磾", "金安上", "窦宪", "金建", "伍孚",
    "金赏", "金敞", "金涉", "金钦",
}


def guess_dynasty(books: list[str]) -> str:
    b = "|".join(books)
    has_hou = any(x in b for x in ("後漢", "后汉", "全後漢"))
    has_qian = any(x in b for x in ("漢書", "史記", "全漢文", "前漢紀"))
    has_san = "三國" in b
    if has_san and not has_hou:
        return "漢魏之際"
    if has_hou:
        return "東漢"
    if has_qian:
        return "西漢"
    return "兩漢"


def next_pid(used: set[str]) -> str:
    i = 1
    while True:
        pid = f"P{i:04d}"
        if pid not in used:
            used.add(pid)
            return pid
        i += 1


def main() -> None:
    if not EV.exists():
        raise SystemExit("run extract_persons_full.py first")

    bucket: dict[str, list[dict]] = defaultdict(list)
    with EV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            bucket[r["person"]].append(r)

    CARDS.mkdir(exist_ok=True)
    existing = {p.stem.split("_")[0] for p in CARDS.glob("*.md")}
    # 收集已用 id
    used_ids = set()
    for p in CARDS.glob("*.md"):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"^id:\s*(\S+)", t, re.M)
        if m:
            used_ids.add(m.group(1))

    made = skipped = 0
    for person, evs in sorted(bucket.items(), key=lambda x: -len(x[1])):
        if person in KEEP_DETAIL or person in existing:
            skipped += 1
            continue
        books = sorted({e["book"] for e in evs})
        dyn = guess_dynasty(books)
        pid = next_pid(used_ids)
        # 最多 8 条出处
        src_lines = []
        seen_q = set()
        for e in evs:
            q = (e.get("sentence") or "").replace('"', "'")[:240]
            key = q[:50]
            if key in seen_q:
                continue
            seen_q.add(key)
            src_lines.append(
                f'  - book: {e.get("book")}\n    juan: {e.get("juan")}\n    quote: 「{q}」'
            )
            if len(src_lines) >= 8:
                break
        body = f"""---
id: {pid}
name: {person}
style_name: 阙
dynasty: {dyn}
status: 草稿
category: 阙
origin: 阙
birth: 阙
death: 阙
shizhong_terms:
  - start: 阙
    end: 阙
    nature: 阙
    evidence: 有明文
sources:
{chr(10).join(src_lines) if src_lines else '  - book: 阙'}
---

## 生平履历

（全量骨架：待人审扩写）

## 侍中任职前后

（待校）

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
|  |  |  |  |

## 校录备注

- 自动抽取 evidence={len(evs)}；书目：{'/'.join(books)}
- cand: data/candidates/persons_evidence.csv
- 校录人/日期：待填
"""
        (CARDS / f"{person}_{dyn}.md").write_text(body, encoding="utf-8")
        made += 1

    print(f"cards made={made} skipped_existing={skipped} total_bucket={len(bucket)}")

    # 全量入库（覆盖式重建 person/source/term，保留 relation/candidate）
    if not DB.exists():
        raise SystemExit("run init_db.py first")
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM shizhong_term")
    cur.execute("DELETE FROM source")
    cur.execute("DELETE FROM person")
    n_p = n_s = 0
    for p in sorted(CARDS.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm_m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not fm_m:
            continue
        fm = fm_m.group(1)
        def grab(k: str) -> str:
            m = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
            return (m.group(1).strip() if m else "")
        pid = grab("id") or p.stem
        name = grab("name") or p.stem.split("_")[0]
        cur.execute(
            """INSERT OR REPLACE INTO person
            (id,name,style_name,dynasty,category,origin,birth,death,status,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, name, grab("style_name"), grab("dynasty"), grab("category"),
                grab("origin"), grab("birth"), grab("death"), grab("status") or "草稿",
                p.name,
            ),
        )
        n_p += 1
        # sources
        for m in re.finditer(
            r"-\s*book:\s*(.+)\n\s*juan:\s*(.+)\n\s*quote:\s*(.+)", fm
        ):
            book, juan, quote = m.group(1).strip(), m.group(2).strip(), m.group(3).strip().strip("「」")
            if book == "阙":
                continue
            cur.execute(
                "INSERT INTO source (book,juan,quote,path) VALUES (?,?,?,?)",
                (book, juan, quote, p.name),
            )
            sid = cur.lastrowid
            n_s += 1
            cur.execute(
                """INSERT OR IGNORE INTO shizhong_term
                (person_id,start_ym,end_ym,nature,evidence,source_id)
                VALUES (?,?,?,?,?,?)""",
                (pid, "阙", "阙", "阙", "有明文", sid),
            )
    con.commit()
    for t in ("person", "source", "shizhong_term", "relation", "candidate"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, cur.fetchone()[0])
    con.close()
    print(f"db person+{n_p} source+{n_s}")


if __name__ == "__main__":
    main()
