"""生平独立存储：从卡片「## 生平履历」抽取，写入 person_bio 表与 data/bio/bio.json。

与 person/shizhong_term/source 分表存放，不混入既有结构字段。
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import t2s

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"
OUT_JSON = ROOT / "data" / "bio" / "bio.json"
OUT_WEB = ROOT / "shizhongdata" / "data" / "bio.json"


def parse_bio(body: str) -> list[str]:
    m = re.search(r"^## 生平履历\s*\n+(.*?)(?=^## |\Z)", body, re.M | re.S)
    if not m:
        return []
    lines = []
    for ln in m.group(1).splitlines():
        s = re.sub(r"^[-*\s]+", "", ln)
        s = re.sub(r"^\d+\.\s*", "", s).strip()
        if s:
            lines.append(t2s(s))
    return lines


def parse_card_id_name(path: Path):
    t = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S)
    if not m:
        return None
    fm, body = m.group(1), m.group(2)

    def grab(k):
        mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
        return mm.group(1).strip() if mm else ""

    return grab("id"), grab("name"), body


def main() -> None:
    rows = []
    for p in sorted(CARDS.glob("*.md")):
        parsed = parse_card_id_name(p)
        if not parsed:
            continue
        pid, name, body = parsed
        if not pid or not name:
            continue
        lines = parse_bio(body)
        # 过滤过短/占位
        text = "\n".join(lines)
        has = 1 if len(text.replace("\n", "")) >= 40 else 0
        rows.append(
            {
                "person_id": pid,
                "name": t2s(name),
                "has_bio": has,
                "lines": lines,
                "char_count": len(text.replace("\n", "")),
            }
        )

    # SQLite 独立表
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS person_bio")
    cur.execute(
        """
        CREATE TABLE person_bio (
            person_id TEXT PRIMARY KEY,
            name TEXT,
            has_bio INTEGER,
            char_count INTEGER,
            bio_lines TEXT,
            updated TEXT DEFAULT (datetime('now'))
        )
        """
    )
    for r in rows:
        cur.execute(
            "INSERT INTO person_bio (person_id, name, has_bio, char_count, bio_lines) VALUES (?,?,?,?,?)",
            (
                r["person_id"],
                r["name"],
                r["has_bio"],
                r["char_count"],
                json.dumps(r["lines"], ensure_ascii=False),
            ),
        )
    con.commit()
    n = cur.execute("SELECT COUNT(*) FROM person_bio WHERE has_bio=1").fetchone()[0]
    con.close()

    payload = {
        "meta": {
            "source": "cards/## 生平履历",
            "note": "独立生平库，与 person/term/source 分离",
            "total": len(rows),
            "with_bio": n,
        },
        "bios": {r["person_id"]: {"name": r["name"], "lines": r["lines"]} for r in rows if r["has_bio"]},
    }
    for out in (OUT_JSON, OUT_WEB):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"bio stored: persons={len(rows)} with_bio={n} -> {OUT_JSON} + {OUT_WEB}")


if __name__ == "__main__":
    main()
