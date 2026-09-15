"""简单查询：按人名 / 关系类型查试点库。

用法:
  python sources/query_db.py --person 金安上
  python sources/query_db.py --rel 举主
  python sources/query_db.py --stats
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "shizhong.db"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--person")
    ap.add_argument("--rel")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    if args.stats:
        for t in ("person", "source", "shizhong_term", "relation", "candidate"):
            cur.execute(f"SELECT COUNT(*) c FROM {t}")
            print(f"{t}: {cur.fetchone()['c']}")
        print("\n-- person by dynasty --")
        for r in cur.execute(
            "SELECT dynasty, COUNT(*) c FROM person GROUP BY dynasty ORDER BY c DESC"
        ):
            print(r["dynasty"], r["c"])
        print("\n-- candidate by status --")
        for r in cur.execute(
            "SELECT status, COUNT(*) c FROM candidate GROUP BY status ORDER BY c DESC"
        ):
            print(r["status"], r["c"])
        return

    if args.person:
        cur.execute("SELECT * FROM person WHERE name LIKE ?", (f"%{args.person}%",))
        for p in cur.fetchall():
            print("===", p["id"], p["name"], p["dynasty"], p["status"], "===")
            for s in cur.execute(
                "SELECT book,juan,quote FROM source s JOIN shizhong_term t ON t.source_id=s.id WHERE t.person_id=?",
                (p["id"],),
            ):
                print(f"  [{s['book']} {s['juan']}] {s['quote'][:80]}")
            for r in cur.execute(
                "SELECT * FROM relation WHERE from_name=? OR to_name=?",
                (p["name"], p["name"]),
            ):
                print(f"  REL {r['from_name']} -{r['rel_type']}-> {r['to_name']} ({r['note']})")
        return

    if args.rel:
        cur.execute(
            "SELECT * FROM relation WHERE rel_type LIKE ?", (f"%{args.rel}%",)
        )
        for r in cur.fetchall():
            print(f"{r['from_name']} -{r['rel_type']}-> {r['to_name']} | {r['note']}")
        return

    ap.error("need --person / --rel / --stats")


if __name__ == "__main__":
    main()
