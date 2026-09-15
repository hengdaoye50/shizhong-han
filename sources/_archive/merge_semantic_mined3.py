"""合并 pass3 挖掘结果到 evidence，并为新出现者建骨架深卡。"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINED = ROOT / "data" / "candidates" / "persons_semantic_mined3.csv"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

EXTRA = {
    "费祎": ("字文伟，江夏鄳人。蜀汉侍中，守尚书令，后为大将军。诸葛亮所重，与蒋琬并列。", "蜀漢", "士人"),
    "董允": ("字休昭。侍中，领虎贲中郎将，统宿卫亲兵。出师表所举。", "蜀漢", "士人"),
    "陈祗": ("代董允为侍中，与黄皓互相表里，皓始预政事。后以侍中守尚书令。", "蜀漢", "其他"),
    "马良": ("字季常。先主以良为侍中；遣安慰五溪蛮夷。", "蜀漢", "士人"),
    "是仪": ("字子羽。吴详、综并为侍中（或为是仪、胡综系）。", "吳", "士人"),
    "胡综": ("与是仪并为侍中（句「详、综并为侍中」）。", "吳", "士人"),
    "荀勖": ("字公曾。魏晋侍中领中书监。", "魏_晉", "士人"),
    "和峤": ("字长舆。侍中，与荀勖至东宫观察太子。", "魏_晉", "士人"),
    "陈群": ("字长文。转为侍中，领丞相东西曹掾。", "魏", "士人"),
    "辛毗": ("字佐治。魏侍中，谏文帝。", "魏", "士人"),
    "陈泰": ("字玄伯。加侍中光禄大夫。", "魏", "士人"),
    "张布": ("吴骠骑将军，加侍中。", "吳", "其他"),
    "周举": ("字宣光。拜为侍中，与杜乔等八使巡行。", "東漢", "士人"),
    "关统": ("弱冠为侍中。蜀汉（关羽系？待考）。", "蜀漢", "勋贵"),
    "廖立": ("字公渊。先主为汉中王，徵立为侍中。", "蜀漢", "士人"),
    "乐松": ("灵帝时侍中祭酒，鸿都门下。", "東漢", "其他"),
    "刁玄": ("吴侍中（亮问侍中刁玄）。", "吳", "其他"),
    "董扶": ("广汉董扶，私谓刘焉京师将乱。", "東漢", "士人"),
    "曹楙": ("楙历位侍中尚书。", "魏", "宗室"),
}


def main() -> None:
    mined = list(csv.DictReader(MINED.open(encoding="utf-8-sig")))
    existing = list(csv.DictReader(EV.open(encoding="utf-8-sig")))
    fields = ["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"]
    have = {(r["person"], r["cand_row"]) for r in existing}
    by = defaultdict(list)
    for r in mined:
        by[r["person"]].append(r)
        key = (r["person"], r["cand_row"])
        if key not in have:
            existing.append({k: r.get(k, "") for k in fields})
            have.add(key)
    with EV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing)
    print("evidence", len(existing), "persons_with_ev", len({r['person'] for r in existing}))

    existing_names = {p.stem.split("_")[0] for p in CARDS.glob("*.md")}
    i = 200
    for person, evs in sorted(by.items(), key=lambda x: -len(x[1])):
        if person in existing_names:
            continue
        i += 1
        bio, dyn, cat = EXTRA.get(person, ("（证据句见 sources；待扩写）", "兩漢", "阙"))
        quotes = []
        seen = set()
        for e in evs:
            q = (e.get("sentence") or "").replace('"', "'")[:200]
            if q[:40] in seen:
                continue
            seen.add(q[:40])
            quotes.append((e.get("book"), e.get("juan"), q))
        src = "\n".join(f"  - book: {b}\n    juan: {j}\n    quote: 「{q}」" for b, j, q in quotes[:6])
        body = f"""---
id: P{i:04d}
name: {person}
style_name: 阙
dynasty: {dyn}
status: 待审
category: {cat}
origin: 阙
birth: 阙
death: 阙
shizhong_terms:
  - start: 阙
    end: 阙
    nature: 见原典
    evidence: 有明文
sources:
{src}
---

## 生平履历

1. {bio}

## 侍中任职前后

- 见原典引文

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
|  |  |  |  |

## 校录备注

- 语义挖人 pass3；evidence={len(evs)}
- 校录人/日期：待填
"""
        (CARDS / f"{person}_{dyn}.md").write_text(body, encoding="utf-8")
        print("new card", person)

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM shizhong_term")
    cur.execute("DELETE FROM source")
    cur.execute("DELETE FROM person")
    for p in sorted(CARDS.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            continue
        fm = m.group(1)

        def grab(k: str) -> str:
            mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
            return mm.group(1).strip() if mm else ""

        cur.execute(
            """INSERT OR REPLACE INTO person
            (id,name,style_name,dynasty,category,origin,birth,death,status,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                grab("id"), grab("name"), grab("style_name"), grab("dynasty"), grab("category"),
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
                (grab("id"), "阙", "阙", "有明文", "有明文", cur.lastrowid),
            )
    con.commit()
    for t in ("person", "source", "shizhong_term"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, cur.fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
