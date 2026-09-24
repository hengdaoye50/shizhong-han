# -*- coding: utf-8 -*-
"""relation 表去重（保留最小 rowid）+ 修复 upsert source 解析幂等。"""
import re
import sqlite3
from pathlib import Path

ROOT = Path(r"D:\CODEX\两汉侍中数据库搭建")
DB = ROOT / "data" / "db" / "shizhong.db"
UPSERT = ROOT / "sources" / "upsert_cards_to_db.py"


def dedup_relation():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    sql = cur.execute("SELECT sql FROM sqlite_master WHERE name='relation'").fetchone()[0]
    print("SCHEMA", sql)
    n0 = cur.execute("SELECT COUNT(*) FROM relation").fetchone()[0]
    # 列名探测
    cols = [r[1] for r in cur.execute("PRAGMA table_info(relation)")]
    print("COLS", cols)
    keys = [c for c in ("from_id", "to_id", "rel_type", "note", "quote") if c in cols]
    key_sql = ", ".join(keys)
    cur.execute(
        f"""
        DELETE FROM relation WHERE rowid NOT IN (
          SELECT MIN(rowid) FROM relation GROUP BY {key_sql}
        )
        """
    )
    n1 = cur.execute("SELECT COUNT(*) FROM relation").fetchone()[0]
    con.commit()
    con.close()
    print(f"relation {n0} -> {n1} (removed {n0 - n1})")


def patch_upsert():
    t = UPSERT.read_text(encoding="utf-8")
    orig = t
    # 1) source 解析：兼容 - quote: 开头
    t = t.replace(
        'if line.strip().startswith("- book:"):',
        'if line.strip().startswith("- book:") or line.strip().startswith("- quote:"):',
    )
    # 若以 - quote: 开头，补 book 空串的初始化分支
    t = t.replace(
        '''            if line.strip().startswith("- book:") or line.strip().startswith("- quote:"):
                if cur_src:
                    data["sources"].append(cur_src)
                cur_src = {
                    "book": line.split(":", 1)[1].strip(),
                    "juan": "",
                    "quote": "",
                }''',
        '''            if line.strip().startswith("- book:") or line.strip().startswith("- quote:"):
                if cur_src:
                    data["sources"].append(cur_src)
                cur_src = {"book": "", "juan": "", "quote": ""}
                if line.strip().startswith("- book:"):
                    cur_src["book"] = line.split(":", 1)[1].strip()
                else:
                    cur_src["quote"] = line.split(":", 1)[1].strip().strip("「」")''',
    )
    # 2) relation 幂等：INSERT 前先查存在
    t = t.replace(
        "n_rel = upsert_default_relations(cur, name_to_id)",
        "n_rel = upsert_default_relations(cur, name_to_id)\n    con.commit()\n"
        "    # 幂等：去掉重复 relation\n"
        "    cur.execute(\"\"\"DELETE FROM relation WHERE rowid NOT IN \"\"\"\n"
        "               \"\"\"(SELECT MIN(rowid) FROM relation \"\"\"\n"
        "               \"\"\" GROUP BY from_id, to_id, rel_type, COALESCE(note,''), COALESCE(quote,''))\"\"\")",
    )
    if t != orig:
        UPSERT.write_text(t, encoding="utf-8")
        print("PATCHED upsert_cards_to_db.py")
    else:
        print("upsert NOCHANGE")


if __name__ == "__main__":
    dedup_relation()
    patch_upsert()
