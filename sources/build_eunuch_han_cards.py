"""皇后纪/佞幸/西汉传新确认侍中建卡。"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

# name: (style, dynasty, category, origin, bio, term, quotes, rels)
NEW = {
    "阎畅": (
        "阙", "東漢", "外戚", "河南",
        [
            "安帝阎皇后之父。以后父为侍中。",
            "三年，以后父侍中畅为长水校尉，封北宜春侯，食邑五千户。",
        ],
        "以后父为侍中，迁长水校尉封侯",
        [("後漢書", "卷十下皇后纪", "以後父侍中暢爲長水校尉，封北宜春侯。")],
        [("阎皇后", "女", "安帝后")],
    ),
    "谢笃": (
        "阙", "東漢", "外戚", "扶风",
        [
            "谢恽之弟。为侍中。",
            "阎显奏耿宝党与：虎贲中郎将谢恽、恽弟侍中笃、笃弟大将军长史宓等更相阿党。",
        ],
        "为侍中（耿宝党与）",
        [("後漢書", "卷十下皇后纪", "惲弟侍中篤、篤弟大將軍長史宓……更相阿黨。")],
        [("谢恽", "兄", "虎贲中郎将")],
    ),
    "阴统": (
        "阙", "東漢", "外戚", "南阳新野",
        [
            "阴康之弟。袭封昆阳侯，位侍中。",
            "阴氏外戚一系。",
        ],
        "袭封昆阳侯，位侍中",
        [("後漢書", "卷十下皇后纪", "以康弟統襲封昆陽侯，位侍中。")],
        [("阴识/阴兴", "宗族", "外戚")],
    ),
    "伏完": (
        "阙", "東漢", "外戚", "琅邪东武",
        [
            "伏湛玄孙。袭爵不其侯，尚桓帝女阳安公主，为侍中。",
            "女伏寿为献帝皇后。完深沉有大度。",
        ],
        "袭爵不其侯，尚主，为侍中",
        [("後漢書", "卷十下皇后纪", "父完，沉深有大度，襲爵不其侯，尚桓帝女陽安公主，爲侍中。")],
        [("阳安公主", "妻", "桓帝女"), ("伏寿", "女", "献帝伏后")],
    ),
    "张彭祖": (
        "阙", "西漢", "佞幸/旧恩", "杜陵",
        [
            "张汤子孙（安世系）。少与宣帝微时同席研书。",
            "帝即尊位，彭祖以旧恩封阳都侯，出常参乘，号为爱幸。",
            "为侍中中郎将。",
        ],
        "侍中中郎将；以旧恩爱幸",
        [("漢書", "卷九十三佞幸傳", "侍中中郎將張彭祖少與帝微時同席研書……以舊恩封陽都侯。")],
        [("宣帝", "与帝", "微时同席"), ("张汤", "先祖", "")],
    ),
    "王去疾": (
        "阙", "西漢", "外戚", "东平陵",
        [
            "平阿侯王谭之子。哀帝为太子时为庶子得幸。",
            "及即位，为侍中、骑都尉。",
        ],
        "为侍中、骑都尉",
        [("漢書", "卷九十三佞幸傳", "唯平阿侯譚子去疾，哀帝爲太子時爲庶子得幸，及即位，爲侍中、騎都尉。")],
        [("王谭", "父", "平阿侯"), ("哀帝", "与帝", "旧幸")],
    ),
    "王闳": (
        "阙", "西漢", "外戚", "东平陵",
        [
            "王氏。哀帝时为侍中、中常侍。",
            "后上置酒麒麟殿，贤父子亲属宴饮，王闳兄弟侍中、中常侍皆在侧。",
        ],
        "为侍中",
        [("漢書", "卷九十三", "王閎兄弟侍中、中常侍皆在側。")],
        [("董贤", "同列", "同时在侧")],
    ),
    "王龚": (
        "阙", "西漢", "士人", "东平陵",
        [
            "光禄勋以外属内卿。与奉车都尉刘歆共校书，三人皆侍中（王龚、刘歆、房凤？）。",
            "西汉末校书近侍。",
        ],
        "为侍中（校书）",
        [("漢書", "卷八十八儒林傳", "光祿勳王龔以外屬內卿，與奉車都尉劉歆共校書，三人皆侍中。")],
        [("刘歆", "同僚", "共校书"), ("房凤", "同僚", "三人皆侍中")],
    ),
    "王忽": (
        "阙", "西漢", "其他", "京兆",
        [
            "卫尉王莽（前汉）之子男。为侍中。",
            "武帝崩，忽扬语：帝崩忽常在左右，安得遗诏封三子事。霍光切让王莽，莽酖杀忽。",
        ],
        "为侍中（昭帝初）",
        [("漢書", "卷六十八霍光金日磾傳", "時衛尉王莽子男忽侍中，揚語曰：『帝崩，忽常在左右，安得遺詔封三子事！』")],
        [("王莽(前汉)", "父", "卫尉"), ("霍光", "政敌", "光让莽杀忽")],
    ),
    "张千秋": (
        "阙", "西漢", "勋贵", "杜陵",
        [
            "张安世子。与弟延寿、彭祖皆中郎将侍中。",
            "宣元以来张氏为侍中、中常侍者十余人。",
        ],
        "中郎将侍中",
        [("漢書", "卷五十九張湯傳", "安世子千秋、延壽、彭祖，皆中郎將侍中。")],
        [("张安世", "父", ""), ("张彭祖", "兄弟", "")],
    ),
    "张延寿": (
        "阙", "西漢", "勋贵", "杜陵",
        [
            "张安世子。中郎将侍中。",
        ],
        "中郎将侍中",
        [("漢書", "卷五十九張湯傳", "安世子千秋、延壽、彭祖，皆中郎將侍中。")],
        [("张安世", "父", "")],
    ),
    "霍山": (
        "阙", "西漢", "外戚", "河东平阳",
        [
            "霍光兄孙（去病孙？光侄孙）。奉车都尉、侍中，领胡越兵。",
            "霍氏败，自杀。",
        ],
        "奉车都尉侍中，领胡越兵",
        [("漢書", "卷六十八霍光金日磾傳", "雲弟山奉車都尉、侍中，領胡、越兵。")],
        [("霍光", "从祖", ""), ("霍禹", "兄弟", "")],
    ),
    "金汤": (
        "阙", "西漢", "降人", "金涉子",
        [
            "金涉子。与弟融皆侍中、诸曹、将、大夫。",
            "金氏七世内侍之一环。",
        ],
        "侍中诸曹将大夫",
        [("漢書", "卷六十八", "涉兩子，湯、融，皆侍中、諸曹、將、大夫。")],
        [("金涉", "父", ""), ("金融", "弟", "亦侍中")],
    ),
    "金融": (
        "阙", "西漢", "降人", "金涉子",
        [
            "金涉子。与兄汤皆侍中、诸曹、将、大夫。",
        ],
        "侍中诸曹将大夫",
        [("漢書", "卷六十八", "涉兩子，湯、融，皆侍中、諸曹、將、大夫。")],
        [("金涉", "父", ""), ("金汤", "兄", "")],
    ),
}


def main() -> None:
    existing = {p.stem.split("_")[0] for p in CARDS.glob("*.md")}
    i = 600
    for person, meta in NEW.items():
        if person in existing:
            print("skip existing", person)
            continue
        i += 1
        style, dyn, cat, origin, bio, term, quotes, rels = meta
        src = "\n".join(f"  - book: {b}\n    juan: {j}\n    quote: 「{q}」" for b, j, q in quotes)
        bio_s = "\n".join(f"{n}. {x}" for n, x in enumerate(bio, 1))
        rel_s = "\n".join(f"| {a} | {b} | {c} | 证据 |" for a, b, c in rels) or "|  |  |  |  |"
        body = f"""---
id: P{i:04d}
name: {person}
style_name: {style}
dynasty: {dyn}
status: 待审
category: {cat}
origin: {origin}
birth: 阙
death: 阙
shizhong_terms:
  - start: 阙
    end: 阙
    nature: {term}
    evidence: 有明文
sources:
{src}
---

## 生平履历

{bio_s}

## 侍中任职前后

- {term}

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
{rel_s}

## 校录备注

- 皇后纪/佞幸/西汉传扫描确认
- 校录人/日期：待填
"""
        (CARDS / f"{person}_{dyn}.md").write_text(body, encoding="utf-8")
        print("card", person)

    # 重建 person/source/term
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
