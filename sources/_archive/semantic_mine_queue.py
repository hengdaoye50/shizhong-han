"""从 unparsed 队列做语义挖人：可确认者直接建卡入 evidence，不劳人工标全表。

只写入「句式明确、人名可定」的条目；拿不准的进 persons_unconfirmed.csv。
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "candidates" / "unparsed_namequeue.csv"
OUT_EV = ROOT / "data" / "candidates" / "persons_semantic_mined.csv"
OUT_UNK = ROOT / "data" / "candidates" / "persons_unconfirmed.csv"

# 人工/语义确认：从句中读出的 (人名, 是否真任侍中)
# True=任职明文; False=误检/自称/冒充; None=存疑
# 匹配用子串
RULES: list[tuple[str, str, str | None, str]] = [
    # (句子含, 人名, 判定, 备注)
    ("召青為建章監", "卫青", "Y", "建章监、侍中"),
    ("召青为建章监", "卫青", "Y", "建章监、侍中"),
    ("大將軍青侍中", "卫青", "Y", "侍中，上踞厕视之"),
    ("大将军青侍中", "卫青", "Y", "侍中"),
    ("少而侍中", "卫青", "Y", "少而侍中贵"),
    ("弟青為侍中", "卫青", "Y", "外戚世家"),
    ("弟青为侍中", "卫青", "Y", ""),
    ("年十八為侍中", "霍去病", "Y", "皇后姊子"),
    ("年十八为侍中", "霍去病", "Y", ""),
    ("少為侍中建章監", "李陵", "Y", "字少卿"),
    ("少为侍中建章监", "李陵", "Y", ""),
    ("買臣以楚辭", "朱买臣", "Y", "与严助俱幸侍中"),
    ("买臣以楚辞", "朱买臣", "Y", ""),
    ("買臣與嚴助俱侍中", "朱买臣", "Y", ""),
    ("买臣与严助俱侍中", "朱买臣", "Y", ""),
    ("嚴助俱侍中", "严助", "Y", ""),
    ("严助俱侍中", "严助", "Y", ""),
    ("荀彘", "荀彘", "Y", "以御见侍中"),
    ("以御見，侍中", "荀彘", "Y", ""),
    ("以御见，侍中", "荀彘", "Y", ""),
    ("放為侍中中郎將", "张放", "Y", "张汤玄孙"),
    ("放为侍中中郎将", "张放", "Y", ""),
    ("征放為侍中", "张放", "Y", ""),
    ("征放为侍中", "张放", "Y", ""),
    ("增少為郎", "韩增", "Y", "诸曹侍中光禄大夫"),
    ("增少为郎", "韩增", "Y", ""),
    ("侍中駙馬都尉樂昌侯王商", "王商", "Y", "乐昌侯"),
    ("侍中驸马都尉乐昌侯王商", "王商", "Y", ""),
    ("光祿大夫樂昌侯王商", "王商", "Y", ""),
    ("光禄大夫乐昌侯王商", "王商", "Y", ""),
    ("高侍中，貴幸", "史高", "Y", "发霍禹功封乐陵侯"),
    ("高侍中，贵幸", "史高", "Y", ""),
    ("陽平侯王鳳為衛尉侍中", "王凤", "Y", ""),
    ("阳平侯王凤为卫尉侍中", "王凤", "Y", ""),
    ("長子鳳嗣侯，為衛尉侍中", "王凤", "Y", ""),
    ("长子凤嗣侯，为卫尉侍中", "王凤", "Y", ""),
    ("引光女婿甄邯為侍中", "甄邯", "Y", "奉车都尉"),
    ("引光女婿甄邯为侍中", "甄邯", "Y", ""),
    ("侍中崇祿侯孔永", "孔永", "Y", "新莽"),
    ("侍中崇禄侯孔永", "孔永", "Y", ""),
    ("伊休侯", "刘棻", "Y", "歆长子，侍中五官中郎将；名从考"),
    ("地餘侍中", "欧阳地余", "Y", "儒林，至少府"),
    ("地余侍中", "欧阳地余", "Y", ""),
    ("侯世子常侍中", "卫伉", "Y", "青长子"),
    ("長子伉", "卫伉", "Y", ""),
    ("长子伉", "卫伉", "Y", ""),
    ("賁赫自以為侍中", "贲赫", "N", "自称，非拜命"),
    ("贲赫自以为侍中", "贲赫", "N", ""),
    ("詐為御史、謁者、侍中", None, "N", "赵高客诈称"),
    ("诈为御史、谒者、侍中", None, "N", ""),
    ("掌牧大夫李棽", "李棽", "Y", "新莽侍中掌牧大夫"),
    ("傅嘉", "傅嘉", "Y", "见前"),
    ("以參為侍中水衡都尉", "王参", "Y", "元后传"),
    ("以参为侍中水衡都尉", "王参", "Y", ""),
    ("成都侯況", "王况", "Y", "列侯侍中"),
    ("成都侯况", "王况", "Y", ""),
    ("侍中、中郎將霍禹", "霍禹", "Y", "右将军前为侍中中郎将"),
    ("侍中、中郎将霍禹", "霍禹", "Y", ""),
    ("平恩侯許嘉", "许嘉", "Y", "车骑将军，曾侍中光禄大夫"),
    ("平恩侯许嘉", "许嘉", "Y", ""),
    ("伯遷水衡都尉，與兩師並侍中", "班伯", "Y", "叙传"),
    ("伯迁水衡都尉，与两师并侍中", "班伯", "Y", ""),
    ("左將軍素侍中", "荀彘", "Y", "朝鲜列传左将军"),
    ("左将军素侍中", "荀彘", "Y", ""),
]


def load_queue() -> list[dict]:
    with QUEUE.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main() -> None:
    rows = load_queue()
    mined: dict[str, list[dict]] = defaultdict(list)
    unconfirmed: list[dict] = []

    for r in rows:
        s = (r.get("sentence") or "").replace(" ", "")
        hit = None
        for key, person, flag, note in RULES:
            if key.replace(" ", "") in s:
                hit = (person, flag, note)
                break
        if hit is None:
            # 保留未命中的，不自动瞎填
            continue
        person, flag, note = hit
        if flag == "N" or person is None:
            unconfirmed.append({**r, "guess": person or "", "note": note})
            continue
        mined[person].append(
            {
                "person": person,
                "cand_row": r.get("cand_row"),
                "book": r.get("book"),
                "juan": r.get("juan"),
                "sentence": r.get("sentence"),
                "source_file": r.get("source_file", ""),
                "alias_in_sentence": note,
            }
        )

    # 写 mined
    fields = ["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"]
    with OUT_EV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for p, evs in sorted(mined.items(), key=lambda x: -len(x[1])):
            for e in evs:
                w.writerow(e)

    with OUT_UNK.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["cand_row", "book", "juan", "sentence", "guess", "note", "person", "status", "review_note"],
        )
        w.writeheader()
        for r in unconfirmed:
            w.writerow(
                {
                    "cand_row": r.get("cand_row"),
                    "book": r.get("book"),
                    "juan": r.get("juan"),
                    "sentence": (r.get("sentence") or "")[:200],
                    "guess": r.get("guess", ""),
                    "note": r.get("note", ""),
                    "person": "",
                    "status": "存疑",
                    "review_note": "",
                }
            )

    print("mined persons", len(mined), "evidence", sum(len(v) for v in mined.values()))
    for p, evs in sorted(mined.items(), key=lambda x: -len(x[1])):
        print(f"  {len(evs):2d} {p}")
    print("unconfirmed", len(unconfirmed), "->", OUT_UNK)


if __name__ == "__main__":
    main()
