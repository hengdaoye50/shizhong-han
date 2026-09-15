"""过滤 context_mined，合并高置信者入 evidence 并建卡。"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINED = ROOT / "data" / "candidates" / "persons_context_mined.csv"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"
OUT_OK = ROOT / "data" / "candidates" / "persons_context_ok.csv"

DROP = {
    "卫青者", "卫皇后", "是正文", "孙皓", "朱建平", "乔卿", "元以来", "郭玉者",
    "王朝", "元以", "任并", "祭酒", "卫尉", "步兵", "博士", "议郎", "太守",
    "刺史", "侍中", "尚书", "将军", "黄门", "于是", "更始", "光武",
}

# 高置信：后汉有传且确曾任侍中/近侍（据证据句与史实）
CONFIRM = {
    "刘昆": ("字桓公，陈留东昏人。光武时拜侍中祭酒，入讲省内。经学家。", "東漢", "士人"),
    "丁恭": None,  # 已有
    "尹敏": ("字幼季，南阳堵阳人。永平初为侍中，数进见问得失。", "東漢", "士人"),
    "张湛": ("字子孝，扶风平陵人。光武时拜侍中，迁太子太傅。以清廉称。", "東漢", "士人"),
    "杜乔": None,  # 已有
    "杨厚": ("字仲桓，广汉新都人。三迁为侍中，特蒙引见，访以时政。方术/儒学。", "東漢", "士人"),
    "桓郁": ("字仲恩，桓荣子。稍迁侍中，以侍中监虎贲中郎将；诏听以侍中行服。", "東漢", "士人"),
    "桓焉": ("字叔元，桓郁子。三迁为侍中步兵校尉。授安帝经。", "東漢", "士人"),
    "贾逵": None,
    "班固": ("字孟坚。拜侍中，从驾南巡；典校秘书，撰《汉书》。", "東漢", "士人"),
    "张衡": ("字平子，南阳西鄂人。后迁侍中，帝引在帷幄，讽议左右；科学家、文学家。", "東漢", "士人"),
    "李法": ("字伯度，汉中南郑人。和帝时历位将军大夫侍中，出为东郡太守。", "東漢", "士人"),
    "江革": ("字次翁，齐国临淄人。建光中公车特征，拜侍中。以孝称「江巨孝」。", "東漢", "士人"),
    "赵典": ("字仲经，蜀郡成都人。少为侍中、虎贲中郎将，朝廷多称其能。", "東漢", "士人"),
    "施延": ("字君子，沛国蕲人。有道高第，拜侍中，后位至太尉。", "東漢", "士人"),
    "刘茂": ("字子卫（一作叔盛），太原晋阳人。光武即位以为侍中、骑都尉。", "東漢", "勋贵"),
    "傅俊": None,  # 已有
    "马武": ("字子张，南阳湖阳人。光武即位以为侍中；云台二十八将之一。", "東漢", "勋贵"),
    "赵憙": ("字伯阳，南阳宛人。光武时为侍中，骑都尉。", "東漢", "勋贵"),
    "蔡茂": ("字子礼，河内怀人。光武征拜侍中，迁广汉太守、司徒。", "東漢", "士人"),
    "郑弘": ("字巨君，会稽山阴人。为侍中，出为平原相，征拜侍中。", "東漢", "士人"),
    "张霸": ("字伯饶，蜀郡成都人。征拜侍中，领骑都尉。", "東漢", "士人"),
    "何休": ("字邵公，任城樊人。经学家，公羊学大师；官至谏议大夫（与侍中系连待考）。", "東漢", "士人"),
    "蔡玄": ("字叔陵，汝南南顿人。顺帝时为侍中。", "東漢", "士人"),
    "李膺": ("字元礼，颍川襄城人。党锢名士；再迁侍中、虎贲中郎将。", "東漢", "士人"),
    "贾彪": ("字伟节，颍川定陵人。党锢名士；三迁侍中。", "東漢", "士人"),
    "谢弼": ("字辅宣，东郡武阳人。稍迁侍中。", "東漢", "士人"),
    "李充": ("字大逊，陈留人。再迁侍中，卒于官。", "東漢", "士人"),
    "孙期": ("字仲彧，济阴成武人。征拜侍中（儒林）。", "東漢", "士人"),
    "杨伦": ("字仲理，陈留东昏人。迁侍中祭酒。", "東漢", "士人"),
    "刘平": ("字公子，楚郡彭城人。拜侍中，迁长乐卫尉。", "東漢", "士人"),
    "赵孝": ("字长平，沛国蕲人。永平中辟太尉府，迁侍中。", "東漢", "士人"),
    "王逸": ("字叔师，南郡宜城人。顺帝时为侍中。著《楚辞章句》。", "東漢", "士人"),
    "陈球": ("字伯真，下邳淮浦人。拜侍中，转执金吾河南尹。", "東漢", "士人"),
    "董扶": None,  # 已有
    "顾雍": ("字元叹，吴郡吴人。吴相；曾为侍中（吴）。", "吳", "士人"),
    "钟兴": ("字次文，汝南汝阳人。少从丁恭受严氏春秋，光武时拜侍中。", "東漢", "士人"),
    "刘植": ("字伯先，巨鹿昌城人。光武以为侍中、骑都尉；云台二十八将。", "東漢", "勋贵"),
    "郭昌": ("东汉初，光武侍中系（待考细节）。", "東漢", "阙"),
    "王歙": ("更始/光武间为侍中（从更始在长安）。", "更始", "阙"),
}


def main() -> None:
    mined = list(csv.DictReader(MINED.open(encoding="utf-8-sig")))
    by = defaultdict(list)
    for r in mined:
        p = r["person"]
        if p in DROP or len(p) < 2:
            continue
        by[p].append(r)

    # 只保留 CONFIRM 键或证据>=2 且不在 DROP
    keep = {}
    for p, evs in by.items():
        if p in CONFIRM and CONFIRM[p] is not None:
            keep[p] = evs
        elif p in CONFIRM and CONFIRM[p] is None:
            continue  # 已有卡
        elif len(evs) >= 2 and p not in DROP:
            # 仍可能噪声，默认不进正式库
            pass

    print("keep", len(keep), "ev", sum(len(v) for v in keep.values()))
    for p, evs in sorted(keep.items(), key=lambda x: -len(x[1])):
        print(f"  {len(evs):2d} {p}")

    # merge evidence
    existing = list(csv.DictReader(EV.open(encoding="utf-8-sig")))
    fields = ["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"]
    have = {(r["person"], str(r.get("cand_row"))) for r in existing}
    for p, evs in keep.items():
        for e in evs:
            key = (p, str(e.get("cand_row")))
            if key in have:
                continue
            existing.append({k: e.get(k, "") for k in fields})
            have.add(key)
    with EV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing)

    # cards
    existing_names = {p.stem.split("_")[0] for p in CARDS.glob("*.md")}
    i = 300
    for person, evs in sorted(keep.items(), key=lambda x: -len(x[1])):
        if person in existing_names:
            continue
        i += 1
        bio, dyn, cat = CONFIRM[person]
        quotes = []
        seen = set()
        for e in evs:
            q = (e.get("sentence") or "").replace('"', "'")[:200]
            if q[:36] in seen:
                continue
            seen.add(q[:36])
            quotes.append((e.get("book"), e.get("juan"), q))
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

- 见 sources 引文与本传

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
|  |  |  |  |

## 校录备注

- 上下文挖人+史实核对；evidence={len(evs)}
- 校录人/日期：待填
"""
        (CARDS / f"{person}_{dyn}.md").write_text(body, encoding="utf-8")
        print("card", person)

    # rebuild db persons
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
