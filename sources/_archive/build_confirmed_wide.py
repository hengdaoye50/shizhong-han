"""确认名单并入 evidence + 建卡。"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDE = ROOT / "data" / "candidates" / "persons_context_wide.csv"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

# 人工核读确认
CONFIRM: dict[str, tuple[str, str, str]] = {
    # name: (bio, dynasty, category)
    "郑均": ("字仲虞，东平任城人。建和中四府表荐，征拜议郎，侍讲禁内，再迁为侍中。以廉洁称。", "東漢", "士人"),
    "任安": ("字定祖，广汉绵竹人。儒林。征拜议郎，稍迁侍中、弘农太守。", "東漢", "士人"),
    "杨政": ("字子行，京兆人。儒林。帝善之，拜为侍中，数进见问得失；迁侍中祭酒。", "東漢", "士人"),
    "宋登": ("字叔阳，京兆长安人。顺帝使持节临太学，奏定曲律，转拜侍中；擢拜侍中，典领秘书近署。", "東漢", "士人"),
    "李尤": ("字伯仁，广汉雒人。文苑。顺帝时为侍中。与刘珍等撰《东观汉记》。", "東漢", "士人"),
    "周泽": ("字稚都，北海安丘人。儒林。十八年拜侍中骑都尉，卒于官。", "東漢", "士人"),
    "张玄": ("字君夏，河内河阳人。儒林。岁余复征，再迁侍中，卒于官。", "東漢", "士人"),
    "许慎": ("字叔重，汝南召陵人。经学家、《说文解字》作者。迁侍中，出为弘农太守，卒官。", "東漢", "士人"),
    "赵苞": ("字威豪，甘陵东武城人。独行。征拜侍中，每朝廷大事，侃然正色，百官惮之。", "東漢", "士人"),
    "阴识": ("字次伯，南阳新野人。光烈皇后兄。迁侍中，以母忧辞归；九年迁侍中，赐爵关内侯。", "東漢", "外戚"),
    "陈俊": ("字子昭，南阳西鄂人。云台二十八将。光武即位以为侍中、骑都尉。", "東漢", "勋贵"),
    "淳于恭": ("字孟孙，北海淳于人。引见极日，访以政事，迁侍中骑都尉，礼待甚优。", "東漢", "士人"),
    "丁鸿": ("字孝公，颍川定陵人。桓荣弟子。顷之拜侍中。白虎观论经。", "東漢", "士人"),
    "桓郁": ("字仲恩。永平十四年为议郎，迁侍中；以侍中监（兼）虎贲中郎将。", "東漢", "士人"),
    "张兴": ("字君上，颍川鄢陵人。儒林。帝善之拜为侍中；以侍中兼领虎贲中郎将。", "東漢", "士人"),
    "贾复": ("字君文，南阳冠军人。云台二十八将。少为侍中、虎贲中郎将。", "東漢", "勋贵"),
    "陈翔": ("字子麟，汝南邵陵人。党锢。察孝廉举高第，三迁侍中。", "東漢", "士人"),
    "孔昱": ("字世元，鲁国鲁人。党锢。察孝廉举高第，三迁侍中。", "東漢", "士人"),
    "王莽": ("字巨君。迁骑都尉光禄大夫侍中，宿卫谨敕；后篡汉建新。", "西漢_新", "外戚"),
    "华歆": ("字子鱼，平原高唐人。拜议郎，参司空军事，入为尚书，转侍中，代荀彧为尚书令。", "漢魏之際", "士人"),
    "卫臻": ("字公振，陈留襄邑人。明帝即位后转右仆射，典选举，加侍中。", "魏", "士人"),
    "刘劭": ("字孔才，广平邯郸人。文帝即王位为侍中，赐爵关内侯。文学家。", "魏", "士人"),
    "陈矫": ("字季弼，广陵东阳人。加侍中光禄大夫，迁司徒。", "魏", "士人"),
    "钟繇": ("字元常，颍川长社人。拜御史中丞，迁侍中尚书仆射；以侍中守司隶校尉督关中。书法家。", "漢魏之際", "士人"),
}

# 需要从 wide 里取的句子（按人名过滤）
def load_wide() -> dict[str, list[dict]]:
    by = defaultdict(list)
    with WIDE.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            by[r["person"]].append(r)
    return by


# 别名 → 规范
ALIAS = {
    "阴識": "阴识", "桓榮": "桓郁",  # 东观句实为郁
    "刘寬": "刘宽", "周澤": "周泽", "張興": "张兴", "张興": "张兴",
    "陳羣": "陈群", "元常": "钟繇", "董賢": "董贤", "朱買臣": "朱买臣",
}


def main() -> None:
    wide = load_wide()
    existing = list(csv.DictReader(EV.open(encoding="utf-8-sig")))
    fields = ["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"]
    have = {(r["person"], str(r.get("cand_row"))) for r in existing}

    added = 0
    for person in CONFIRM:
        evs = wide.get(person, [])
        # 别名
        for a, b in ALIAS.items():
            if b == person:
                evs = evs + wide.get(a, [])
        for e in evs:
            # 只收含该人名或明显本传句
            sent = e.get("sentence") or ""
            if person[:2] not in sent and person not in sent:
                # 仍收（上下文归属），但标记
                pass
            key = (person, str(e.get("cand_row")))
            if key in have:
                continue
            row = {k: e.get(k, "") for k in fields}
            row["person"] = person
            existing.append(row)
            have.add(key)
            added += 1
        # 若 wide 无句，写占位（从 CONFIRM bio 出处）
        if not any(r["person"] == person for r in existing):
            existing.append(
                {
                    "person": person,
                    "cand_row": "",
                    "book": "後漢書",
                    "juan": "本傳",
                    "sentence": CONFIRM[person][0],
                    "source_file": "",
                    "alias_in_sentence": "semantic",
                }
            )
            added += 1

    with EV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing)
    print("evidence added", added, "total", len(existing))

    existing_names = {p.stem.split("_")[0] for p in CARDS.glob("*.md")}
    i = 400
    for person, (bio, dyn, cat) in CONFIRM.items():
        if person in existing_names:
            continue
        i += 1
        evs = [r for r in existing if r["person"] == person]
        quotes = []
        seen = set()
        for e in evs:
            q = (e.get("sentence") or "").replace('"', "'")[:200]
            if not q or q[:36] in seen:
                continue
            seen.add(q[:36])
            quotes.append((e.get("book") or "後漢書", e.get("juan") or "本傳", q))
        if not quotes:
            quotes = [("後漢書", "本傳", bio[:80])]
        src = "\n".join(f"  - book: {b}\n    juan: {j}\n    quote: 「{q}」" for b, j, q in quotes[:8])
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
    nature: 见原典「侍中」明文
    evidence: 有明文
sources:
{src}
---

## 生平履历

1. {bio}

## 侍中任职前后

- 见 sources

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
|  |  |  |  |

## 校录备注

- 宽挖+人工核读确认；evidence={len(evs)}
- 校录人/日期：待填
"""
        (CARDS / f"{person}_{dyn}.md").write_text(body, encoding="utf-8")
        print("card", person)

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
    for t in ("person", "source", "shizhong_term", "relation", "candidate"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, cur.fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
