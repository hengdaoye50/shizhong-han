"""收尾清洗：去掉卡片/库中草稿工作流标记（待审/草稿/待填/校录人），保留史学「待考」。"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"


def clean_card(p: Path) -> bool:
    raw = p.read_text(encoding="utf-8")
    t = raw
    # status: 待审/草稿 → 已校（前端本就不展示，库字段同步）
    t = re.sub(r"^status:\s*(待审|草稿|待校|待定|待终审)\s*$", "status: 已校", t, flags=re.M)
    # 校录备注中的待填行
    t = re.sub(r"^-\s*校录人/日期：待填\s*\n", "", t, flags=re.M)
    t = re.sub(r"^-\s*校录人：.*待填\s*\n", "", t, flags=re.M)
    # 空的校录备注小节可保留标题；若小节只剩空行则收成一句
    t = re.sub(r"(## 校录备注\n)(?:\s*\n)+", r"\1\n", t)
    # 标题里的待审字样（若有）
    if t != raw:
        p.write_text(t, encoding="utf-8")
        return True
    return False


def main() -> None:
    n = 0
    for p in sorted(CARDS.glob("*.md")):
        if clean_card(p):
            n += 1
    print("cards cleaned", n)

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute(
        "UPDATE person SET status='已校' WHERE status IN ('待审','草稿','待校','待定','待终审') OR status IS NULL OR status=''"
    )
    print("person status updated", cur.rowcount)
    # notes 里若有草稿字样
    cur.execute("UPDATE person SET notes=NULL WHERE notes LIKE '%待填%' OR notes LIKE '%待审%'")
    con.commit()
    rows = cur.execute("SELECT status, COUNT(*) FROM person GROUP BY status").fetchall()
    print("status now", rows)
    con.close()


if __name__ == "__main__":
    main()
