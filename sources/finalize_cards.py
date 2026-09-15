"""收尾：清注疏、补遗关键卡、重建库与导出。"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

# 定点重写（去注疏 + 补履历）
REWRITE = {
    "杨琦": ("東漢", "阙", "士人", "阙", "阙", "阙", "献帝时侍中", [
        "献帝朝侍中。李傕乱中随驾。",
        "李傕移乘舆幸北坞，**侍中杨琦上封事**，言傕边鄙之人习于夷风，常有怏怏之色。",
        "使琦高举车帷。与丁冲、钟繇等同行。",
    ], [
        ("三國志", "卷6董二袁劉傳", "李傕移乘輿幸北塢，侍中楊琦上封事"),
        ("三國志", "卷6", "使侍中楊琦高舉車帷"),
        ("後漢紀", "卷28", "侍中楊琦上封事曰傕邊鄙之人習於夷風"),
    ], [("献帝", "与帝", "随驾"), ("李傕", "政敌", "上封事言傕")]),
    "王粲": ("漢魏之際", "仲宣", "士人", "山阳高平", "177", "217", "魏侍中", [
        "字仲宣，山阳高平人。建安七子之一。博物多识，问无不对。",
        "以西京扰乱，依刘表。表卒，劝表子琮归曹操。",
        "操辟为丞相掾，赐爵关内侯。魏国既建，拜侍中。从军作五言诗以美其事。",
        "博物洽闻，识旧珮，始复作之。建安二十二年春卒，年四十一。",
    ], [
        ("三國志", "卷21王卫二刘傅传", "是行也，侍中王粲作五言詩以美其事"),
        ("三國志", "卷21", "魏侍中王粲識舊珮，始復作之"),
    ], [("曹操", "府主", "丞相掾"), ("曹丕", "与帝", "魏侍中"), ("建安七子", "同列", "文学")]),
    "耿纪": ("漢魏之際", "季行", "士人", "扶风茂陵", "阙", "218", "献帝时侍中", [
        "字季行，耿弇后。少为侍中。",
        "建安二十三年，与丞相司直韦晃等起兵诛曹操，欲挟天子以攻魏。事败，夷三族。",
    ], [
        ("三國志", "卷23和常杨杜赵裴傳", "後至許，見侍中耿紀，語終夜"),
        ("後漢書", "卷19耿弇传", "侍中耿紀與丞相司直韋晃等起兵誅操"),
    ], [("耿弇", "先祖", "云台"), ("曹操", "政敌", "起兵被夷三族")]),
    "荀顗": ("魏_晉", "景倩", "士人", "颍川颍阴", "阙", "274", "魏侍中；晋太尉", [
        "字景倩，颍川颍阴人，荀彧子。少知名，博学洽闻，理思周密。",
        "魏时以父勋为中郎。司马懿辅政，见顗奇之，擢拜散骑侍郎，累迁侍中。",
        "与崔赞、袁亮、钟毓等讲述礼典。武帝使侍中荀顗、和峤至东宫观察太子。",
        "晋受禅，进位公，为太尉、行太子太傅。泰始十年卒，谥康。",
    ], [
        ("三國志", "卷10荀彧攸贾诩傳", "帝宴羣臣於太極東堂，與侍中荀顗……講述禮典"),
        ("三國志", "卷10", "武帝使侍中荀顗、和嶠俱至東宮，觀察太子"),
    ], [("荀彧", "父", "尚书令"), ("司马炎", "与帝", "晋太尉"), ("和峤", "同僚", "观太子")]),
    "郑称": ("漢魏之際", "阙", "士人", "阙", "阙", "阙", "魏侍中；武德侯傅", [
        "魏侍中。以侍中郑称为武德侯傅（曹叡为武德侯时）。",
        "令曰：龙渊、太阿出昆吾之金，和氏之璧由井里之田——喻贤才须琢磨。",
    ], [
        ("三國志", "卷02文帝纪注引魏略", "以侍中鄭稱爲武德侯傅"),
    ], [("曹叡", "与帝", "为武德侯傅"), ("曹丕", "与帝", "黄初中")]),
    "王允": ("東漢", "子师", "士人", "太原祁", "137", "192", "献帝时为侍中守尚书令", [
        "字子师，太原祁人。世仕州郡为冠盖。同郡郭林宗称其有王佐才。",
        "灵帝时为豫州刺史、侍御史。中平元年拜豫州刺史，讨黄巾。",
        "献帝即位，拜太仆，守尚书令。**初平三年，与吕布诛董卓**，录尚书事，总朝政。",
        "卓将李傕、郭汜攻长安，允被杀，宗族夷灭。",
    ], [
        ("後漢書", "卷96王允传", "王允字子師，太原祁人也"),
        ("後漢書", "卷96", "與呂布誅卓……允乃自比陳蕃、竇武"),
        ("後漢書", "卷72董卓傳", "侍中黃門不得出入"),
    ], [("吕布", "同谋", "诛卓"), ("董卓", "政敌", "诛卓"), ("献帝", "与帝", "录尚书事")]),
    "何进": ("東漢", "遂高", "外戚", "南阳宛", "阙", "189", "拜侍中将作大匠河南尹；大将军", [
        "字遂高，南阳宛人。屠家子。妹为灵帝皇后。",
        "光和三年，贵人立为皇后，**征进入，拜侍中、将作大匠、河南尹**。",
        "中平元年为大将军，讨黄巾。灵帝崩，欲诛宦官，谋泄，为张让等所杀。",
    ], [
        ("後漢書", "卷99窦何传", "何進字遂高，南陽宛人也"),
        ("後漢書", "卷99", "拜侍中、將作大匠、河南尹"),
    ], [("何皇后", "妹", "灵帝后"), ("窦武", "先例", "并谋诛宦官"), ("张让", "政敌", "杀进")]),
    "邓骘": ("東漢", "昭伯", "外戚", "南阳新野", "阙", "121", "大将军（举侍中鲁丕）", [
        "字昭伯，南阳新野人，邓禹孙。妹为和熹皇后。",
        "永初元年封上蔡侯，为车骑将军、仪同三司。**大将军邓骘举鲁丕**，再迁复为侍中。",
        "建光元年，安帝乳母王圣等谮邓氏，骘免特进，徙封罗侯，不食而死。",
    ], [
        ("後漢書", "卷46邓寇传", "大將軍鄧騭舉丕，再遷，復爲侍中"),
        ("後漢書", "卷16", "鄧騭字昭伯"),
    ], [("邓禹", "祖", "云台之首"), ("和熹邓皇后", "妹", ""), ("鲁丕", "所举", "侍中")]),
    "袁隗": ("東漢", "次阳", "士人", "汝南汝阳", "阙", "190", "太傅（表郑玄为侍中未行）", [
        "字次阳，汝南汝阳人，袁安孙。少历显位。",
        "灵帝时为司徒、太傅。**后将军袁隗表郑玄为侍中**，玄以父丧不行。",
        "初平元年，董卓胁迁都，隗为太傅录尚书事。二年为卓所害。",
    ], [
        ("後漢書", "卷65张曹郑传", "後將軍袁隗表爲侍中，以父喪不行"),
        ("後漢書", "卷75袁张韩周传", "袁隗字次陽"),
    ], [("袁安", "祖", "司空"), ("袁绍", "从子", ""), ("郑玄", "所表", "被表未行")]),
}


def main() -> None:
    name_to_file = {}
    for p in CARDS.glob("*.md"):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"^name:\s*(.+)$", t, re.M)
        if m:
            name_to_file[m.group(1).strip()] = p

    for person, meta in REWRITE.items():
        dyn, style, cat, origin, birth, death, nature, bio, quotes, rels = meta
        old = name_to_file.get(person)
        pid = None
        if old and old.exists():
            t = old.read_text(encoding="utf-8")
            m = re.search(r"^id:\s*(\S+)", t, re.M)
            if m:
                pid = m.group(1)
            old.unlink()
        if not pid:
            pid = f"P15{abs(hash(person)) % 100:02d}"
        dyn_tag = dyn.replace("/", "_")
        src = "\n".join(f"  - book: {b}\n    juan: {j}\n    quote: 「{q}」" for b, j, q in quotes)
        bio_s = "\n".join(f"{n}. {x}" for n, x in enumerate(bio, 1))
        rel_s = "\n".join(f"| {a} | {b} | {c} | 本传 |" for a, b, c in rels)
        body = f"""---
id: {pid}
name: {person}
style_name: {style}
dynasty: {dyn_tag}
status: 待审
category: {cat}
origin: {origin}
birth: {birth}
death: {death}
shizhong_terms:
  - start: 阙
    end: 阙
    nature: {nature}
    evidence: 有明文
sources:
{src}
---

## 生平履历

{bio_s}

## 侍中任职前后

- {nature}

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
{rel_s}

## 校录备注

- 收尾重写：去注疏、补履历
- 校录人/日期：待填
"""
        (CARDS / f"{person}_{dyn_tag}.md").write_text(body, encoding="utf-8")
        print("ok", person)

    # 全局再剥一次注疏
    NOTE = re.compile(r"（注[:：][^）]*）|（案[:：][^）]*）")
    for p in CARDS.glob("*.md"):
        t = p.read_text(encoding="utf-8")
        t2 = NOTE.sub("", t)
        if t2 != t:
            p.write_text(t2, encoding="utf-8")

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM shizhong_term")
    cur.execute("DELETE FROM source")
    for p in sorted(CARDS.glob("*.md")):
        t = p.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
        if not m:
            continue
        fm = m.group(1)
        pid_m = re.search(r"^id:\s*(\S+)", fm, re.M)
        if not pid_m:
            continue
        pid = pid_m.group(1)
        for sm in re.finditer(r"-\s*book:\s*(.+)\n\s*juan:\s*(.+)\n\s*quote:\s*(.+)", fm):
            b, j, q = sm.group(1).strip(), sm.group(2).strip(), sm.group(3).strip().strip("「」")
            if b == "阙" or "（注" in q:
                continue
            cur.execute(
                "INSERT INTO source (book,juan,quote,path) VALUES (?,?,?,?)",
                (b, j, q[:400], p.name),
            )
            cur.execute(
                """INSERT OR IGNORE INTO shizhong_term
                (person_id,start_ym,end_ym,nature,evidence,source_id)
                VALUES (?,?,?,?,?,?)""",
                (pid, "阙", "阙", "有明文", "有明文", cur.lastrowid),
            )
    con.commit()
    for t in ("person", "source", "shizhong_term", "relation"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, cur.fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
