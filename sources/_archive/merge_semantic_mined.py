"""合并 semantic_mined 到主 evidence，并为新人写深卡。"""

from __future__ import annotations

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MINED = ROOT / "data" / "candidates" / "persons_semantic_mined.csv"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

NEW_FACTS = {
    "卫青": dict(
        id="P0100", dynasty="西漢", style="仲卿", category="外戚/勋贵",
        origin="河东平阳", birth="阙", death="前106",
        term="建章监、侍中；后为大将军",
        bio=[
            "字仲卿，河东平阳人。卫皇后弟。",
            "上召青为建章监，侍中；及同母昆弟贵，赏赐累千金。",
            "大将军青侍中，上踞厕视之——近侍之极。",
            "后为车骑将军、大将军，击匈奴，封长平侯。",
        ],
        rels=[("卫子夫", "姊", "皇后"), ("武帝", "与帝", "近侍→大将"), ("霍去病", "外甥", "")],
    ),
    "霍去病": dict(
        id="P0101", dynasty="西漢", style="阙", category="外戚/勋贵",
        origin="河东平阳", birth="前140", death="前117",
        term="年十八为侍中；后为骠骑将军",
        bio=[
            "卫皇后姊子。年十八为侍中。",
            "善骑射，再从大将军击匈奴，封冠军侯，为骠骑将军。",
            "少而侍中，贵不省士。",
        ],
        rels=[("卫青", "舅", ""), ("武帝", "与帝", "")],
    ),
    "李陵": dict(
        id="P0102", dynasty="西漢", style="少卿", category="勋贵",
        origin="陇西成纪", birth="阙", death="阙",
        term="少为侍中、建章监",
        bio=[
            "字少卿，李广孙。少为侍中、建章监。",
            "善骑射，后将兵击匈奴，兵败降。",
        ],
        rels=[("李广", "祖", ""), ("武帝", "与帝", "")],
    ),
    "朱买臣": dict(
        id="P0103", dynasty="西漢", style="翁子", category="士人",
        origin="会稽吴", birth="阙", death="阙",
        term="与严助俱幸，为侍中，后为太中大夫、会稽太守",
        bio=[
            "字翁子，会稽吴人。家贫好读书，以《楚辞》得幸。",
            "买臣与严助俱幸，侍中，为太中大夫，用事。",
            "后拜会稽太守，击破东越，官至主爵都尉。",
        ],
        rels=[("严助", "同僚", "俱侍中"), ("武帝", "与帝", "")],
    ),
    "严助": dict(
        id="P0104", dynasty="西漢", style="阙", category="士人",
        origin="会稽吴", birth="阙", death="前122",
        term="与朱买臣俱侍中、贵用事",
        bio=[
            "会稽吴人，严忌子（一说族子）。郡举贤良对策，擢为中大夫。",
            "与朱买臣等俱侍中，贵用事。后坐淮南王交私，弃市。",
        ],
        rels=[("朱买臣", "同僚", ""), ("武帝", "与帝", "")],
    ),
    "张放": dict(
        id="P0105", dynasty="西漢", style="阙", category="外戚/佞幸",
        origin="杜陵", birth="阙", death="阙",
        term="为侍中中郎将，监平乐屯兵；复征为侍中光禄大夫",
        bio=[
            "张汤玄孙，富平侯。成帝宠臣。",
            "为侍中、中郎将，监平乐屯兵，置莫府，仪比将军。",
            "后复征为侍中光禄大夫，秩中二千石。",
        ],
        rels=[("成帝", "与帝", "宠臣"), ("张汤", "先祖", "")],
    ),
    "韩增": dict(
        id="P0106", dynasty="西漢", style="阙", category="勋贵",
        term="少为郎、诸曹侍中光禄大夫；昭帝时至前将军",
        bio=[
            "韩王信之后。少为郎，诸曹、侍中、光禄大夫。",
            "昭帝时至前将军，与霍光定策立宣帝，益封千户。",
        ],
        rels=[("霍光", "同僚", "定策"), ("宣帝", "与帝", "定策功")],
    ),
    "王商": dict(
        id="P0107", dynasty="西漢", style="子夏", category="外戚",
        origin="东平陵", term="侍中驸马都尉；后为右将军、丞相",
        bio=[
            "字子夏，宣帝舅乐昌侯王武之子（一说成帝丞相王商）。",
            "为侍中、驸马都尉。上使侍中驸马都尉乐昌侯王商诘问贾捐之。",
            "后至右将军、丞相，与王凤不协，免相呕血死。",
        ],
        rels=[("王凤", "政敌", "凤谮商"), ("元帝/成帝", "与帝", "")],
    ),
    "史高": dict(
        id="P0108", dynasty="西漢", style="阙", category="外戚",
        term="侍中，贵幸；发举霍禹功封乐陵侯",
        bio=[
            "宣帝祖母史良娣家。为侍中，贵幸。",
            "发举反者大司马霍禹，封乐陵侯。与金安上共发霍氏。",
        ],
        rels=[("金安上", "同僚", "共发霍氏"), ("霍禹", "政敌", ""), ("宣帝", "与帝", "外戚")],
    ),
    "王凤": dict(
        id="P0109", dynasty="西漢", style="孝卿", category="外戚",
        origin="东平陵", term="卫尉侍中；后大司马大将军领尚书事",
        bio=[
            "字孝卿，元后兄。阳平侯。",
            "为卫尉侍中；太子长舅，与皇后太子忧惧。",
            "后为大司马大将军领尚书事，王氏专权之始。",
        ],
        rels=[("王政君", "妹", "元后"), ("成帝", "与帝", "元舅")],
    ),
    "甄邯": dict(
        id="P0110", dynasty="西漢/新", style="阙", category="外戚",
        term="孔光女婿，引为侍中奉车都尉",
        bio=[
            "孔光女婿。王莽盛尊事光，引甄邯为侍中奉车都尉。",
            "及为侍中，建白诛讨定陵侯淳于长大逆罪。新莽重臣。",
        ],
        rels=[("孔光", "岳父", ""), ("王莽", "府主", ""), ("淳于长", "政敌", "建白诛讨")],
    ),
    "孔永": dict(
        id="P0111", dynasty="新", style="阙", category="其他",
        term="侍中崇禄侯，为宁始将军",
        bio=["新莽侍中、崇禄侯。宁始将军姚恂免，以孔永为宁始将军。"],
        rels=[("王莽", "与帝系", "")],
    ),
    "刘棻": dict(
        id="P0112", dynasty="新", style="阙", category="士人",
        term="侍中五官中郎将（伊休侯）",
        bio=["刘歆长子，伊休侯。为侍中五官中郎将，莽素爱之。"],
        rels=[("刘歆", "父", ""), ("王莽", "与帝系", "爱之")],
    ),
    "班伯": dict(
        id="P0113", dynasty="西漢", style="阙", category="士人",
        term="水衡都尉，与两师并侍中，秩中二千石",
        bio=["班氏。迁水衡都尉，与许商、师丹并侍中，皆秩中二千石。"],
        rels=[("许商", "同列", ""), ("师丹", "同列", "")],
    ),
    "王参": dict(
        id="P0114", dynasty="西漢", style="阙", category="外戚",
        term="侍中水衡都尉",
        bio=["王氏。以参为侍中水衡都尉。"],
        rels=[("王氏", "宗族", "")],
    ),
    "王况": dict(
        id="P0115", dynasty="西漢", style="阙", category="外戚",
        term="成都侯，列侯侍中",
        bio=["成都侯王况，以外亲继父为列侯侍中。"],
        rels=[("王氏", "宗族", "")],
    ),
    "霍禹": dict(
        id="P0116", dynasty="西漢", style="阙", category="外戚",
        term="侍中中郎将；后为右将军、大司马",
        bio=["霍光子。为侍中、中郎将。光薨后为右将军，嗣博陆侯，后谋反诛。"],
        rels=[("霍光", "父", ""), ("宣帝", "与帝", "霍氏败")],
    ),
    "卫伉": dict(
        id="P0117", dynasty="西漢", style="阙", category="外戚/勋贵",
        term="侯世子，常侍中，贵幸",
        bio=["卫青长子，长平侯世子。常侍中，贵幸。"],
        rels=[("卫青", "父", "")],
    ),
    "李棽": dict(
        id="P0118", dynasty="新", style="阙", category="其他",
        term="侍中掌牧大夫，拜大将军扬州牧，赐名圣",
        bio=["新莽侍中掌牧大夫。拜大将军、扬州牧，赐名圣，使将兵。"],
        rels=[("王莽", "与帝系", "")],
    ),
    "欧阳地余": dict(
        id="P0119", dynasty="西漢", style="阙", category="士人",
        term="元帝即位后侍中，贵幸，至少府",
        bio=["儒林欧阳氏。元帝即位，地余侍中，贵幸，至少府。"],
        rels=[("元帝", "与帝", "")],
    ),
}


def load_mined() -> dict[str, list[dict]]:
    b = defaultdict(list)
    with MINED.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            b[r["person"]].append(r)
    return b


def main() -> None:
    mined = load_mined()
    # 合并进主 evidence（追加，不重复 cand_row+person）
    existing = []
    if EV.exists():
        with EV.open(encoding="utf-8-sig") as f:
            existing = list(csv.DictReader(f))
    have = {(r["person"], r["cand_row"]) for r in existing}
    fields = ["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"]
    for p, evs in mined.items():
        for e in evs:
            key = (e["person"], e["cand_row"])
            if key in have:
                continue
            existing.append({k: e.get(k, "") for k in fields})
            have.add(key)
    with EV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing)
    print("evidence total", len(existing))

    # 写新卡
    for person, meta in NEW_FACTS.items():
        evs = mined.get(person, [])
        quotes = []
        seen = set()
        for e in evs:
            q = (e.get("sentence") or "").replace('"', "'")[:220]
            if q[:40] in seen:
                continue
            seen.add(q[:40])
            quotes.append((e.get("book"), e.get("juan"), q))
        if not quotes:
            quotes = [("阙", "阙", "（见 mined evidence）")]
        src = "\n".join(f"  - book: {b}\n    juan: {j}\n    quote: 「{q}」" for b, j, q in quotes)
        bio = "\n".join(f"{i}. {x}" for i, x in enumerate(meta["bio"], 1))
        rel_rows = "\n".join(f"| {a} | {b} | {c} | 证据 |" for a, b, c in meta["rels"])
        dyn = meta["dynasty"].replace("/", "_")
        body = f"""---
id: {meta['id']}
name: {person}
style_name: {meta['style']}
dynasty: {dyn}
status: 待审
category: {meta['category']}
origin: {meta.get('origin', '阙')}
birth: {meta.get('birth', '阙')}
death: {meta.get('death', '阙')}
shizhong_terms:
  - start: 阙
    end: 阙
    nature: {meta['term']}
    evidence: 有明文
sources:
{src}
---

## 生平履历

{bio}

## 侍中任职前后

- {meta['term']}

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
{rel_rows}

## 校录备注

- 语义挖掘建卡；evidence={len(evs)}
- 校录人/日期：待填
"""
        (CARDS / f"{person}_{dyn}.md").write_text(body, encoding="utf-8")
        print("card", person)

    # 重建 DB person/source/term（保留 relation/candidate）
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

        pid = grab("id") or p.stem
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
    for t in ("person", "source", "shizhong_term"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, cur.fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
