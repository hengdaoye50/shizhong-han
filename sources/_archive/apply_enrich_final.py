# -*- coding: utf-8 -*-
"""争议项收尾：徐宣/李仁/荀悦收源；王莽霍光条维持拒收。"""
from pathlib import Path
import re

ROOT = Path(r"D:\CODEX\两汉侍中数据库搭建")
CARDS = ROOT / "data" / "cards"

ACCEPTS = {
    "徐宣": [
        ("「后加侍中光禄大夫」", "三國志", "卷22"),
    ],
    "李仁": [
        ("「吳平後，晉侍中庾峻等問皓侍中李仁曰」", "三國志", "卷48"),
    ],
    "荀悦": [
        ("「漢祕書監侍中荀悅」", "前漢紀", "卷000"),
        ("「侍中悅上《漢紀》」", "前漢紀", "卷030"),
    ],
}

DYNASTY = {"徐宣": "汉魏之际", "李仁": "吴", "荀悦": "东汉"}


def find_card(name: str):
    for p in CARDS.glob("*.md"):
        t = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^name:\s*(.+)$", t, re.M)
        if m and m.group(1).strip() == name:
            return p
    return None


def make_card(name: str, entries):
    dyn = DYNASTY.get(name, "东汉")
    quotes = "\n".join(
        f"  - quote: {q}\n    book: {b}\n    juan: {j}\n" for q, b, j in entries
    )
    body = f"""---
id: P0270
name: {name}
style_name: 悦
dynasty: {dyn}
status: 已校
category: 士人
origin: 阙
birth: 阙
death: 阙
shizhong_terms:
  - start: 阙
    end: 阙
    nature: 秘书监侍中（前汉纪自署）
    evidence: 有明文
sources:
{quotes}---
## 生平履历

1. 字仲豫，颍川颍阴人（荀淑孙、荀俭子）。
2. 侍中、秘书监；撰《汉纪》三十篇。
3. 余履历阙疑，不以推断写入。

## 侍中任职前后

- 见 sources

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
|  |  |  |  |

## 校录备注

- enrich 拒项改判收源（2026-09 人工审定）：前汉纪自署「秘书监侍中荀悦」。
"""
    p = CARDS / f"{name}_東漢.md"
    p.write_text(body, encoding="utf-8")
    print("CREATED", p.name)


def patch(name: str, entries):
    p = find_card(name)
    if not p:
        if name == "荀悦":
            make_card(name, entries)
            return
        print("MISSING", name)
        return
    t = p.read_text(encoding="utf-8")
    added = 0
    for quote, book, juan in entries:
        if quote[:10] in t:
            continue
        block = f"  - quote: {quote}\n    book: {book}\n    juan: {juan}\n"
        if "sources:\n" in t:
            t = t.replace("sources:\n", "sources:\n" + block, 1)
        else:
            t = t.replace("shizhong_terms:", f"sources:\n{block}shizhong_terms:", 1)
        added += 1
    if added:
        note = f"enrich 争议项改判收源 {added} 条（2026-09 用户裁决）"
        if note not in t:
            if "## 校录备注" in t:
                t = t.replace("## 校录备注\n", f"## 校录备注\n\n- {note}\n", 1)
            else:
                t = t.rstrip() + f"\n\n## 校录备注\n\n- {note}\n"
        if "evidence: 有明文" not in t:
            t = re.sub(r"(    evidence: ).*", r"\1有明文", t, count=1)
        p.write_text(t, encoding="utf-8")
        print(f"PATCHED {name} +{added}")
    else:
        print(f"NOCHANGE {name}")


if __name__ == "__main__":
    for n, e in ACCEPTS.items():
        patch(n, e)
    print("DONE")
