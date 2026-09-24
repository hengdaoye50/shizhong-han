# -*- coding: utf-8 -*-
"""按 2026-09 待考审定（网络核证后）批量改卡。只写 nature/evidence/备注措辞。"""
from pathlib import Path
import re

ROOT = Path(r"D:\CODEX\两汉侍中数据库搭建")
CARDS = ROOT / "data" / "cards"

# A 组：网络核证后处置
# keep_restore: 张兴/是仪 有明文，改回侍中
# que: 落阙疑，移出侍中名录统计
ACTIONS = {
    "何休_東漢.md": {
        "nature": "侍中系连阙疑（本传无侍中；儒林下「育」条句非本人）",
        "evidence": "阙疑",
        "repls": [
            ("与侍中之系连待考，不作定说。", "与侍中之系连阙疑，不作定说。"),
            ("何休与侍中系连待考（卡源审计修正）", "何休与侍中系连阙疑（网络核证：百科/本传仕履止于谏议大夫，无侍中）"),
        ],
    },
    "孙期_東漢.md": {
        "nature": "无侍中明文（举方正、终于家）",
        "evidence": "阙疑",
        "repls": [
            ("侍中任职待考（卡源审计修正）", "无侍中明文，落阙疑（网络核证：本传终于家，无侍中）"),
        ],
    },
    "张兴_東漢.md": {
        "nature": "永平初迁侍中祭酒",
        "evidence": "有明文",
        "repls": [
            ("见原典「侍中」明文", "永平初迁侍中祭酒"),
        ],
        "add_quote": "「永平初，迁侍中祭酒。十年，拜太子少傅」",
        "add_source_note": "原典核验：《后汉书》卷79上张兴本传「永平初，迁侍中祭酒」；网络核证（维基文库）确认，改回有明文。",
    },
    "张玄_東漢.md": {
        "nature": "无侍中明文（明经文学/县丞/博士）",
        "evidence": "阙疑",
        "repls": [
            ("东汉儒林；侍中任职待考（勿用他传「岁余复征」句）", "东汉儒林；无侍中明文，落阙疑（勿用他传「岁余复征」句）"),
        ],
    },
    "是仪_吳.md": {
        "nature": "守侍中；嘉禾中拜侍中、中执法",
        "evidence": "有明文",
        "repls": [
            ("吴臣（详综句已剔除；侍中任职待考）", "吴臣；守侍中，嘉禾中拜侍中、中执法"),
            ("原挂「详、综并为侍中」，非是仪本传；是仪仕履以吴书本传为准，侍中任职待考（卡源审计修正）",
             "原挂「详、综并为侍中」已剔；本传明文「守侍中」「拜侍中、中执法」（网络核证《三国志》卷62）"),
            ("「吴详、综并为侍中」类摘句与是仪系连待考，不作定说。",
             "「吴详、综并为侍中」类摘句与是仪无涉，已剔。"),
        ],
        "add_quote": "「荆州平定后拜裨将军，封都亭侯，守侍中」",
        "add_source_note": "原典核验：《三国志》卷62是仪传「守侍中」「拜侍中、中执法」；网络核证确认，改回有明文。",
    },
    "萧育_東漢.md": {
        "nature": "无侍中明文（西汉光禄大夫/执金吾）",
        "evidence": "阙疑",
        "dynasty": "西汉",
        "repls": [
            ("再迁侍中", "无侍中明文（西汉）"),
            ("同句多卡误挂（卡源审计修正）", "同句多卡误挂；网络核证：西汉萧望之子，官至执金吾，无侍中"),
        ],
    },
    "许慎_東漢.md": {
        "nature": "无侍中明文（经学家）",
        "evidence": "阙疑",
        "repls": [
            ("经学家（五经无双）；侍中任职待考", "经学家（五经无双）；无侍中明文，落阙疑"),
        ],
    },
    "钟兴_東漢.md": {
        "nature": "无侍中明文（郎中/左中郎将）",
        "evidence": "阙疑",
        "repls": [
            ("光武时经学家；拜郎中/左中郎将（侍中任职待考）", "光武时经学家；拜郎中/左中郎将，无侍中明文，落阙疑"),
        ],
    },
    "郭昌_東漢.md": {
        "nature": "侍中任职阙疑（摘句或系卫青僚属；非东汉光武侍中）",
        "evidence": "阙疑",
        "repls": [
            ("任职待考（卡内摘句或系卫青，不作定说）", "任职阙疑（摘句或系卫青僚属；网络核证郭昌为西汉武帝时云中将军，非东汉光武侍中）"),
            ("东汉初，光武侍中系（细节待考）。", "网络核证：郭昌为西汉武帝时将军（云中人，从卫青）；与东汉光武侍中系无涉，细节阙疑。"),
        ],
    },
    "关统_蜀漢.md": {
        "nature": "关兴子嗣；尚公主，官至虎贲中郎将（非侍中）",
        "evidence": "推断",
        "repls": [
            ("关羽后裔（世系细节待考，不作定说）。", "关羽后裔（世系细节阙疑，不作定说）。"),
        ],
    },
    # B 组：保留，清触发词
    "丁冲_漢魏之際.md": {
        "repls": [
            ("字里、余仕履阙；建卡时保持「待考」，不将他处丁氏事迹混入。",
             "字里、余仕履阙疑；不将他处丁氏事迹混入。"),
        ],
    },
    "应璩_魏.md": {
        "repls": [
            ("原卡「璩（待考）」已考定**：抽取句「璩六十一为侍中」出朱建平传，「璩」为**应璩**之名，非姓氏待考；「建平」为人名（朱建平），曾被误读为年号。",
             "原卡占位「璩」已并入应璩：抽取句「璩六十一为侍中」出朱建平传，「璩」为应璩之名；「建平」为人名（朱建平），曾被误读为年号。"),
        ],
    },
    "李祯_漢魏之際.md": {
        "repls": [
            ("乱世近侍个案；余履历阙，保持待考。", "乱世近侍个案；余履历阙疑。"),
        ],
    },
    "郤巡_東漢.md": {
        "repls": [
            ("学传英业（樊英之学系，待考）。", "学传英业（樊英之学系，阙疑）。"),
        ],
    },
    "郭举_東漢.md": {
        "repls": [
            ("两条郭举是否一人，史家有疑，建卡时并存待考。", "两条郭举是否一人，史家有疑，并存阙疑。"),
        ],
    },
    "张霸_東漢.md": {
        "repls": [
            ("「八年复为侍中」与郑弘条重叠，暂去挂靠待核（卡源审计修正）",
             "「八年复为侍中」与郑弘条重叠，已去挂靠（不作张霸履历）"),
        ],
    },
}


def patch(path: Path, act: dict):
    t = path.read_text(encoding="utf-8")
    orig = t
    if "nature" in act:
        t = re.sub(r"^(    nature: ).*$", lambda m: m.group(1) + act["nature"], t, count=1, flags=re.M)
        t = re.sub(r"^(    evidence: ).*$", lambda m: m.group(1) + act["evidence"], t, count=1, flags=re.M)
    if "dynasty" in act:
        t = re.sub(r"^(dynasty: ).*$", lambda m: m.group(1) + act["dynasty"], t, count=1, flags=re.M)
    for a, b in act.get("repls", []):
        if a not in t:
            print(f"  MISS in {path.name}: {a[:40]}...")
        t = t.replace(a, b)
    if act.get("add_quote"):
        q = act["add_quote"]
        if q not in t:
            # 在 sources 块前插入 quote 行（与既有 card 结构一致：quote 挂在 source 项下）
            t = t.replace(
                "sources:\n  - book:",
                f"sources:\n  - quote: {q}\n    book:",
                1,
            )
    if act.get("add_source_note"):
        n = act["add_source_note"]
        if n not in t:
            if "## 校录备注" in t:
                t = t.replace("## 校录备注\n", f"## 校录备注\n\n- {n}\n", 1)
            else:
                t = t.rstrip() + f"\n\n## 校录备注\n\n- {n}\n"
    if t != orig:
        path.write_text(t, encoding="utf-8")
        print("PATCHED", path.name)
    else:
        print("NOCHANGE", path.name)


def main():
    for fn, act in ACTIONS.items():
        p = CARDS / fn
        if not p.exists():
            print("MISSING", fn)
            continue
        patch(p, act)
    print("DONE", len(ACTIONS))


if __name__ == "__main__":
    main()
