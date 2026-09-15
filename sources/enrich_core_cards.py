"""为审读后核心人物写高质量卡片（联网要点 + 本库证据），并补回试点已认可人名。"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"

# 试点已认可、自动抽取可能漏掉的人
FORCE_PERSONS = {
    "金日磾": {
        "id": "P0001",
        "dynasty": "西漢",
        "style": "翁叔",
        "category": "降人",
        "origin": "匈奴休屠王太子，没入官，后贵显",
        "birth": "阙",
        "death": "前86",
        "term": "元狩中后为侍中驸马都尉光禄大夫；后为车骑将军",
        "bio": [
            "匈奴休屠王太子。昆邪杀休屠王降汉，日磾没入官，输黄门养马，时年十四。",
            "武帝游宴见马，拜马监，迁侍中驸马都尉光禄大夫，出入骖乘，甚见信爱。",
            "察觉侍中仆射莽何罗（马何罗）谋逆，与霍光、上官桀共讨之；以功封秺侯。",
            "武帝遗诏辅政，为车骑将军。不受封，病困，霍光白封，卧受印绶，一日薨。",
            "子赏、建俱为侍中；金氏七世内侍。",
        ],
        "rels": [
            ("金賞", "子", "嗣侯，为侍中"),
            ("金建", "子", "为侍中、驸马都尉"),
            ("金安上", "从子", "伦支，少为侍中"),
            ("霍光", "同僚", "共受遗诏；光以女妻赏"),
            ("武帝", "与帝", "近侍亲信"),
            ("莽何羅", "政敌", "侍中仆射谋反，日磾讨之"),
        ],
        "quotes": [
            ("漢書", "卷068", "遷侍中駙馬都尉光祿大夫。日磾既親近，未甞有過失，上甚信愛之。"),
            ("漢書", "卷068", "日磾兩子，賞、建，俱侍中，與昭帝略同年，共卧起。"),
            ("漢書", "卷068", "以駙馬都尉發覺侍中莽何羅反侯。"),
        ],
    },
    "金建": {
        "id": "P0004",
        "dynasty": "西漢",
        "style": "阙",
        "category": "降人",
        "origin": "日磾次子",
        "birth": "阙",
        "death": "阙",
        "term": "昭帝时与兄赏俱为侍中；建为驸马都尉",
        "bio": [
            "金日磾次子。与兄金赏俱为侍中，与昭帝略同年，共卧起。",
            "赏为奉车都尉，建为驸马都尉。昭帝论兄弟不可俱佩两绶。",
        ],
        "rels": [
            ("金日磾", "父", ""),
            ("金賞", "兄", "俱侍中"),
            ("昭帝", "与帝", "略同年，共卧起"),
        ],
        "quotes": [
            ("漢書", "卷068", "日磾兩子，賞、建，俱侍中……賞爲奉車、建駙馬都尉。"),
        ],
    },
    "鲁丕": {
        "id": "P0012",
        "dynasty": "東漢",
        "style": "叔陵",
        "category": "士人",
        "origin": "扶風平陵（一說琅邪）",
        "birth": "阙",
        "death": "阙",
        "term": "永初二年邓骘举，再迁复为侍中、左中郎将",
        "bio": [
            "东汉儒者。永初二年，诏公卿举儒术笃学者，大将军邓骘举丕。",
            "再迁，复为侍中、左中郎将，再为三老。帝召诸儒，丕与侍中贾逵等相难。",
        ],
        "rels": [
            ("邓騭", "举主", "大将军举丕"),
            ("贾逵", "同僚", "召诸儒相难"),
        ],
        "quotes": [
            ("後漢書", "卷二十五", "大將軍鄧騭舉丕，再遷，復為侍中、左中郎將，再為三老。"),
            ("東觀漢記", "阙", "帝召諸儒魯丕與侍中賈逵尚書令黃香等相難。"),
        ],
    },
    "梁不疑": {
        "id": "P0011",
        "dynasty": "東漢",
        "style": "阙",
        "category": "外戚",
        "origin": "安定乌氏",
        "birth": "阙",
        "death": "阙",
        "term": "为侍中（梁冀弟）",
        "bio": [
            "大将军梁冀之弟，官侍中。冀威权倾朝，遣不疑以车马珍玩致遗杨厚，欲与相见。",
        ],
        "rels": [
            ("梁冀", "兄", "外戚权臣"),
            ("杨厚", "交游", "冀遣不疑致遗"),
        ],
        "quotes": [
            ("後漢書", "卷二十上", "大將軍梁冀威權傾朝，遣弟侍中不疑以車馬、珍玩致遺於厚。"),
        ],
    },
    "伍孚": {
        "id": "P0021",
        "dynasty": "東漢",
        "style": "德瑜",
        "category": "士人",
        "origin": "阙",
        "birth": "阙",
        "death": "约192",
        "term": "何进辟东曹属，稍迁侍中、河南尹、越骑校尉",
        "bio": [
            "大将军何进辟为东曹属，稍迁侍中、河南尹、越骑校尉。",
            "董卓作乱，孚藏刀刺卓，不中，被收，不屈而死。",
        ],
        "rels": [
            ("何進", "举主", "辟东曹属"),
            ("董卓", "政敌", "谋刺"),
        ],
        "quotes": [
            ("三國志", "卷06", "後大將軍何進辟爲東曹屬，稍遷侍中、河南尹、越騎校尉。"),
        ],
    },
}

# 高证据：据本库证据 + 联网核对扩写
ENRICH = {
    "窦宪": {
        "id": "P0010",
        "dynasty": "東漢",
        "style": "伯度",
        "category": "外戚",
        "origin": "扶风平陵",
        "birth": "阙",
        "death": "92",
        "term": "和帝即位以侍中干机密；永元元年迁车骑将军伐北匈奴，后为大将军",
        "bio": [
            "字伯度，扶风平陵人。窦融曾孙，章德皇后兄。东汉外戚、权臣、将领。",
            "和帝即位，太后临朝，宪以侍中内干机密，出宣诰命。",
            "荐张林为尚书；与司徒袁安、太尉宋由等冲突；刺杀都乡侯畅。",
            "永元元年，拜车骑将军，与耿秉北伐匈奴，登燕然山刻石勒功。",
            "还，为大将军，封武阳侯（让不受）。威权震朝，永元四年败，自杀。",
        ],
        "rels": [
            ("章德竇皇后", "外戚", "皇后兄"),
            ("和帝", "与帝", "少主，宪以外戚重"),
            ("窦太后", "外戚", "临朝称制"),
            ("张林", "举主", "荐为尚书"),
            ("陈宠", "政敌", "斥林阿附"),
            ("崔骃", "府主", "文章往来"),
            ("郭举", "姻亲", "女弟婿为侍中"),
            ("耿秉", "同僚", "副车骑北伐"),
        ],
        "quotes": [
            ("後漢書", "卷二十三", "和帝即位，太后臨朝，憲以侍中，內干機密，出宣誥命。"),
            ("後漢書", "卷五", "以侍中竇憲爲車騎將軍，伐北匈奴。"),
            ("後漢書", "卷二十三", "皇后弟侍中竇憲，薦真定令張林爲尚書。"),
            ("後漢紀", "卷13", "竇憲、耿秉……銘燕然山而還。即拜憲爲大將軍。"),
        ],
        "web": "https://zh.wikipedia.org/zh-hans/窦宪",
    },
    "金安上": {
        "id": "P0002",
        "dynasty": "西漢",
        "style": "子侯",
        "category": "降人",
        "origin": "匈奴休屠后裔（金伦子）",
        "birth": "阙",
        "death": "前56",
        "term": "少为侍中；后至建章卫尉，封都成侯",
        "bio": [
            "金日磾弟金伦之子，字子侯。原为匈奴休屠胡人后裔。",
            "年轻时担任侍中，惇笃有智，得汉宣帝爱重。",
            "参与发举楚王延寿反谋，赐爵关内侯。",
            "霍氏谋反，安上传禁门闼，无内霍氏亲属；与史高建发其事，封都成侯，至建章卫尉。",
            "使谕意萧望之，并与杨恽等诘问望之。谥敬侯。四子：常、敞、岑、明。",
        ],
        "rels": [
            ("金日磾", "从父", "伦支"),
            ("金敞", "子", "后为侍中"),
            ("宣帝", "与帝", "少为侍中见爱"),
            ("霍氏", "政敌", "拒亲属入禁门"),
            ("史高", "同僚", "共发霍氏"),
            ("萧望之", "同僚/被诘", "谕意、诘问"),
        ],
        "quotes": [
            ("漢書", "卷068", "安上字子侯，少爲侍中，惇篤有智，宣帝愛之。"),
            ("漢書", "卷068", "後霍氏反，安上傳禁門闥，無內霍氏親屬，封爲都成侯，至建章衞尉。"),
            ("漢書", "卷068", "侍中史高與金安上建發其事……皆讎有功。"),
        ],
        "web": "https://zh.wikipedia.org/zh-hans/金安上",
    },
    "贾逵": {
        "id": "P0030",
        "dynasty": "東漢",
        "style": "景伯",
        "category": "士人",
        "origin": "扶风平陵（一作汝南）",
        "birth": "30",
        "death": "101",
        "term": "和帝时为侍中（荐尤等）；经学家",
        "bio": [
            "东汉经学家、天文学家。字景伯。",
            "和帝时为侍中，荐尤有相如、扬雄之风。",
            "永元中与鲁丕等诸儒论难；领侍中，前后所著经传训诂百余万言。",
        ],
        "rels": [
            ("鲁丕", "同僚", "诸儒相难"),
            ("和帝", "与帝", "侍中近臣"),
        ],
        "quotes": [
            ("後漢書", "卷三十六", "和帝時，侍中賈逵薦尤有相如、楊雄之風。"),
            ("東觀漢記", "阙", "帝召諸儒魯丕與侍中賈逵……相難。"),
        ],
    },
    "董贤": {
        "id": "P0031",
        "dynasty": "西漢",
        "style": "圣卿",
        "category": "其他",
        "origin": "云阳",
        "birth": "前23",
        "death": "前1",
        "term": "哀帝宠臣，为侍中驸马都尉（佞幸）",
        "bio": [
            "字圣卿，云阳人。哀帝宠臣，出则参乘，入御左右。",
            "为侍中驸马都尉，二十余岁官至大司马卫将军，封高安侯。",
            "哀帝崩，王莽劾其罪，自杀。属佞幸系统，与正途侍中对照鲜明。",
        ],
        "rels": [
            ("哀帝", "与帝", "宠幸无比"),
            ("王莽", "政敌", "莽执政后诛贤"),
        ],
        "quotes": [
            ("漢書", "卷九十三", "董賢……爲侍中駙馬都尉。"),
            ("前漢紀", "阙", "董賢貴幸……"),
        ],
    },
    "淳于长": {
        "id": "P0032",
        "dynasty": "西漢",
        "style": "子孺",
        "category": "外戚",
        "origin": "魏郡元城",
        "birth": "阙",
        "death": "前8",
        "term": "成帝时为侍中（外戚/佞幸边缘）",
        "bio": [
            "字子孺，元城人。太后姊子，成帝时为黄门郎，迁侍中。",
            "以赵飞燕立后事有功，封定陵侯。后坐大逆，死狱中。",
        ],
        "rels": [
            ("成帝", "与帝", ""),
            ("王莽", "政敌", "莽发其奸"),
        ],
        "quotes": [
            ("漢書", "卷九十三", "淳于長……遷侍中。"),
        ],
    },
    "刘瑜": {
        "id": "P0013",
        "dynasty": "東漢",
        "style": "季节",
        "category": "士人",
        "origin": "广陵",
        "birth": "阙",
        "death": "168",
        "term": "窦武引为侍中；后与武同被诛",
        "bio": [
            "字季节，广陵人。好经学，善天文。",
            "窦武引为侍中，与谋诛宦官。素善天文，与陈蕃书言星辰错乱。",
            "建宁元年，曹节等矫诏诛窦武、陈蕃、尹勋、刘瑜等，夷其族。",
        ],
        "rels": [
            ("窦武", "举主", "引为侍中"),
            ("尹勋", "同僚", "共谋诛宦官"),
            ("陈蕃", "同僚", "书信论天文"),
        ],
        "quotes": [
            ("後漢書", "卷六十九", "武於是引同志尹勳爲尚書令，劉瑜爲侍中。"),
            ("後漢書", "卷八", "中常侍曹節矯詔誅太傅陳蕃、大將軍竇武及尚書令尹勳、侍中劉瑜。"),
        ],
    },
    "杜乔": {
        "id": "P0033",
        "dynasty": "東漢",
        "style": "叔荣",
        "category": "士人",
        "origin": "河内林虑",
        "birth": "阙",
        "death": "147",
        "term": "汉安元年与侍中杜乔等八人巡行；乔曾为侍中",
        "bio": [
            "字叔荣。汉安元年，拜光禄大夫，与侍中杜乔等八人同日受诏，案行天下。",
            "号曰「八俊」。后为太尉，不附梁冀，被谮死狱中。",
        ],
        "rels": [
            ("梁冀", "政敌", "不附冀"),
            ("周举", "同僚", "八使之列"),
        ],
        "quotes": [
            ("後漢書", "卷六十三", "拜光祿大夫，與侍中杜喬等八人同日受詔，持節分出，案行天下。"),
        ],
    },
    "史丹": {
        "id": "P0034",
        "dynasty": "西漢",
        "style": "君仲",
        "category": "外戚",
        "origin": "鲁国",
        "birth": "阙",
        "death": "阙",
        "term": "元成间为侍中，护太子（成帝）",
        "bio": [
            "字君仲，鲁国人。以外属为侍中，护太子家。",
            "元帝欲废太子，丹以亲密臣得侍视疾，候上间独寝时伏青蒲上涕泣谏，太子遂得不废。",
            "成帝即位，擢为长乐卫尉，迁右将军，封武阳侯。",
        ],
        "rels": [
            ("元帝", "与帝", "青蒲泣谏"),
            ("成帝", "与帝", "旧护太子"),
            ("王凤", "政敌/对照", "外戚王氏用事"),
        ],
        "quotes": [
            ("漢書", "卷八十二", "史丹……爲侍中。上以丹舊臣皇考外屬，親信之。"),
        ],
    },
}


def load_evidence() -> dict[str, list[dict]]:
    bucket: dict[str, list[dict]] = {}
    if not EV.exists():
        return bucket
    cur = None
    with EV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            bucket.setdefault(r["person"], []).append(r)
    return bucket


def write_card(person: str, meta: dict, quotes: list[tuple], extra_bio: list[str], rels: list[tuple]) -> Path:
    dyn = meta["dynasty"]
    src = "\n".join(
        f'  - book: {b}\n    juan: {j}\n    quote: 「{q}」' for b, j, q in quotes
    )
    bio = "\n".join(f"{i+1}. {x}" for i, x in enumerate(extra_bio))
    rel_rows = "\n".join(f"| {a} | {b} | {c} | 自动/联网 |" for a, b, c in rels)
    body = f"""---
id: {meta['id']}
name: {person}
style_name: {meta.get('style','')}
dynasty: {dyn}
status: 待审
category: {meta.get('category','')}
origin: {meta.get('origin','')}
birth: {meta.get('birth','')}
death: {meta.get('death','')}
shizhong_terms:
  - start: 阙
    end: 阙
    nature: {meta.get('term','')}
    evidence: 有明文
sources:
{src}
---

## 生平履历

{bio}

## 侍中任职前后

- {meta.get('term','（待校）')}

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
{rel_rows}

## 校录备注

- 高质量重建（证据句 + 联网核对要点）
- web: {meta.get('web','')}
- 校录人/日期：待填
"""
    path = CARDS / f"{person}_{dyn}.md"
    path.write_text(body, encoding="utf-8")
    return path


def main() -> None:
    CARDS.mkdir(exist_ok=True)
    ev = load_evidence()
    made = []

    for person, meta in FORCE_PERSONS.items():
        quotes = meta["quotes"]
        # 若本库有更多证据句，附加
        for e in ev.get(person, [])[:4]:
            q = (e.get("sentence") or "")[:200]
            if q and all(q[:30] not in x[2] for x in quotes):
                quotes = quotes + [(e.get("book"), e.get("juan"), q)]
        write_card(person, meta, quotes, meta["bio"], meta["rels"])
        made.append(person)

    for person, meta in ENRICH.items():
        quotes = meta["quotes"]
        for e in ev.get(person, [])[:5]:
            q = (e.get("sentence") or "")[:200]
            if q and all(q[:30] not in x[2] for x in quotes):
                quotes = quotes + [(e.get("book"), e.get("juan"), q)]
        write_card(person, meta, quotes, meta["bio"], meta["rels"])
        made.append(person)

    # 其余 canonical 保持骨架，仅保证存在
    # 入库 person/source/term
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM shizhong_term")
    cur.execute("DELETE FROM source")
    cur.execute("DELETE FROM person")
    n = 0
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
        n += 1
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
                (pid, "阙", "阙", grab("nature") or "阙", "有明文", cur.lastrowid),
            )
    con.commit()
    print("enriched/made", made)
    print("person cards in db", n)
    for t in ("person", "source", "shizhong_term"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, cur.fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
