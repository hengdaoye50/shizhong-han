"""从卡片「关系」表与证据句批量生成 relation 边，写入 SQLite。

优先级：世系/姻亲 → 举主 → 与帝/权臣 → 前后任
"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"
OUT = ROOT / "data" / "db" / "relations_full.csv"

# 关系类型规范
REL_TYPES = {
    "父", "母", "子", "女", "兄弟", "从父", "从子", "祖", "曾祖", "高祖",
    "夫妻", "妻", "夫", "姻亲", "外戚", "尚主", "姊妹",
    "举主", "府主", "师", "同门",
    "政敌", "同僚", "前后任", "同谋",
    "与帝", "与大将军", "与宦官",
    "宗族", "先祖", "兄弟", "从兄", "从弟", "舅", "甥",
}


def parse_front(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm = m.group(1)

    def grab(k: str) -> str:
        mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
        return mm.group(1).strip() if mm else ""

    return {
        "id": grab("id"),
        "name": grab("name"),
        "dynasty": grab("dynasty"),
        "status": grab("status"),
    }


def parse_rel_table(text: str) -> list[tuple[str, str, str, str]]:
    """从 markdown 表格抽 (对象, 类型, 说明, 出处)"""
    rows = []
    if "## 关系" not in text:
        return rows
    part = text.split("## 关系", 1)[1]
    if "## " in part:
        part = part.split("## ", 1)[0]
    for line in part.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0] in ("对象", "---") or set(cells[0]) <= {"-", " "}:
            continue
        if not cells[0]:
            continue
        obj = cells[0]
        rtype = cells[1] if len(cells) > 1 else ""
        note = cells[2] if len(cells) > 2 else ""
        src = cells[3] if len(cells) > 3 else ""
        rows.append((obj, rtype, note, src))
    return rows


def main() -> None:
    person_by_name = {}
    all_rels = []

    for p in sorted(CARDS.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        meta = parse_front(text)
        name = meta.get("name") or p.stem.split("_")[0]
        pid = meta.get("id") or ""
        person_by_name[name] = pid
        for obj, rtype, note, src in parse_rel_table(text):
            all_rels.append(
                {
                    "from_id": pid,
                    "from_name": name,
                    "to_id": "",
                    "to_name": obj,
                    "rel_type": rtype,
                    "note": note,
                    "source": src,
                    "status": "草稿",
                    "card": p.name,
                }
            )

    # 回填 to_id
    for r in all_rels:
        r["to_id"] = person_by_name.get(r["to_name"], "")

    # 去重 (from_name, to_name, rel_type)
    seen = set()
    uniq = []
    for r in all_rels:
        key = (r["from_name"], r["to_name"], r["rel_type"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    # 写 CSV
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["from_id", "from_name", "to_id", "to_name", "rel_type", "note", "source", "status", "card"],
        )
        w.writeheader()
        w.writerows(uniq)

    # 入库
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM relation")
    for r in uniq:
        cur.execute(
            """INSERT INTO relation
            (from_id,from_name,to_id,to_name,rel_type,note,status)
            VALUES (?,?,?,?,?,?,?)""",
            (r["from_id"], r["from_name"], r["to_id"], r["to_name"], r["rel_type"], r["note"][:200], r["status"]),
        )
    con.commit()
    cur.execute("SELECT COUNT(*) FROM relation")
    print("relation rows", cur.fetchone()[0])
    # 类型分布
    cur.execute("SELECT rel_type, COUNT(*) c FROM relation GROUP BY rel_type ORDER BY c DESC")
    for t, c in cur.fetchall():
        print(f"  {c:4d}  {t}")
    cur.execute("SELECT COUNT(*) FROM relation WHERE to_id != ''")
    print("linked both", cur.fetchone()[0])
    con.close()
    print("->", OUT, "cards", len(person_by_name), "uniq", len(uniq))


if __name__ == "__main__":
    main()
