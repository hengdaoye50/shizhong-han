"""为 data/cards/*.md 重新分配唯一 id，并重建 person/source/term。"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"


def main() -> None:
    files = sorted(CARDS.glob("*.md"))
    for i, p in enumerate(files, start=1):
        text = p.read_text(encoding="utf-8")
        new_id = f"P{i:04d}"
        if re.search(r"^id:\s*\S+", text, re.M):
            text = re.sub(r"^id:\s*\S+", f"id: {new_id}", text, count=1, flags=re.M)
        else:
            text = text.replace("---\n", f"---\nid: {new_id}\n", 1)
        p.write_text(text, encoding="utf-8")

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM shizhong_term")
    cur.execute("DELETE FROM source")
    cur.execute("DELETE FROM person")
    for p in files:
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            continue
        fm = m.group(1)

        def grab(k: str) -> str:
            mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
            return mm.group(1).strip() if mm else ""

        pid = grab("id")
        cur.execute(
            """INSERT OR REPLACE INTO person
            (id,name,style_name,dynasty,category,origin,birth,death,status,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, grab("name"), grab("style_name"), grab("dynasty"), grab("category"),
                grab("origin"), grab("birth"), grab("death"), grab("status") or "待审", p.name,
            ),
        )
        for sm in re.finditer(r"-\s*book:\s*(.+)\n\s*juan:\s*(.+)\n\s*quote:\s*(.+)", fm):
            book, juan, quote = sm.group(1).strip(), sm.group(2).strip(), sm.group(3).strip().strip("「」")
            if book == "阙":
                continue
            cur.execute(
                "INSERT INTO source (book,juan,quote,path) VALUES (?,?,?,?)",
                (book, juan, quote, p.name),
            )
            cur.execute(
                """INSERT OR IGNORE INTO shizhong_term
                (person_id,start_ym,end_ym,nature,evidence,source_id)
                VALUES (?,?,?,?,?,?)""",
                (pid, "阙", "阙", "有明文", "有明文", cur.lastrowid),
            )
    con.commit()
    for t in ("person", "source", "shizhong_term", "relation", "candidate"):
        cur.execute(f"SELECT COUNT(*) c FROM {t}")
        print(t, cur.fetchone()[0])
    # 抽查窦宪
    cur.execute(
        """SELECT s.quote FROM source s
           JOIN shizhong_term t ON t.source_id=s.id
           JOIN person p ON p.id=t.person_id
           WHERE p.name=? LIMIT 5""",
        ("窦宪",),
    )
    print("窦宪 sample quotes:")
    for r in cur.fetchall():
        print(" ", r[0][:70])
    con.close()


if __name__ == "__main__":
    main()
