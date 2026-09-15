"""从卡片 front matter 重灌 shizhong_term.nature / start / end。"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"


def parse_fm(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm = m.group(1)

    def grab(k: str) -> str:
        mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
        return mm.group(1).strip() if mm else ""

    # shizhong_terms 块
    nature = start = end = evidence = ""
    in_t = False
    for line in fm.splitlines():
        if line.startswith("shizhong_terms:"):
            in_t = True
            continue
        if in_t:
            if line and not line[0].isspace() and not line.strip().startswith("-"):
                in_t = False
                continue
            s = line.strip()
            if s.startswith("- start:"):
                start = s.split(":", 1)[1].strip()
            elif s.startswith("end:"):
                end = s.split(":", 1)[1].strip()
            elif s.startswith("nature:"):
                nature = s.split(":", 1)[1].strip()
            elif s.startswith("evidence:"):
                evidence = s.split(":", 1)[1].strip()
    return {
        "id": grab("id"),
        "name": grab("name"),
        "nature": nature or "阙",
        "start": start or "阙",
        "end": end or "阙",
        "evidence": evidence or "有明文",
    }


def nature_primary(n: str) -> str:
    if "加官" in n:
        return "加官"
    if "正職" in n or "正职" in n:
        return "正職"
    if "僕射" in n or "仆射" in n or "复合" in n:
        return "复合官"
    if "被表" in n or "未任" in n or "未就" in n:
        return "被表未行"
    if "奉车" in n or "驸马" in n or "駙馬" in n:
        return "近侍兼官"
    return "其他"


def parse_year(s: str):
    if not s:
        return None
    m = re.match(r"前(\d+)", s.strip())
    if m:
        return -int(m.group(1))
    m = re.search(r"(前)?(\d{1,4})", s)
    if m:
        y = int(m.group(2))
        return -y if m.group(1) else y
    return None


def main() -> None:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    n = 0
    for p in sorted(CARDS.glob("*.md")):
        meta = parse_fm(p.read_text(encoding="utf-8"))
        pid = meta.get("id")
        if not pid:
            continue
        np = nature_primary(meta["nature"])
        sy = parse_year(meta["start"])
        ey = parse_year(meta["end"])
        ev = meta["evidence"]
        # 更新该 person 的全部 term（简化：一人一 term 为主）
        cur.execute(
            "UPDATE shizhong_term SET nature=?, nature_primary=?, start_ym=?, end_ym=?, evidence=?, start_year=?, end_year=? WHERE person_id=?",
            (meta["nature"][:120], np, meta["start"][:40], meta["end"][:40], ev, sy, ey, pid),
        )
        n += cur.rowcount
    con.commit()
    cur.execute("SELECT nature_primary, COUNT(*) FROM shizhong_term GROUP BY nature_primary ORDER BY 2 DESC")
    print("nature_primary:")
    for a, b in cur.fetchall():
        print(f"  {b:4d} {a}")
    cur.execute("SELECT COUNT(*) FROM shizhong_term WHERE start_year IS NOT NULL OR end_year IS NOT NULL")
    print("terms with year", cur.fetchone()[0])
    con.close()
    print("updated rows", n)


if __name__ == "__main__":
    main()
