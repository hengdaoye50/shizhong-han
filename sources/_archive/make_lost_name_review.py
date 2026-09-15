"""生成散佚姓氏/待核审读表：data/candidates/lost_name_review.csv

只保留：姓佚、名不全、或无法对到已有卡的条目。
列: row_id, book, juan, sentence, guess_name, decision, canonical_name, note
decision: 确认建卡 | 并入已有 | 非侍中 | 制度条 | 无法判断
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "candidates" / "anonymous_shizhong.csv"
OUT = ROOT / "data" / "candidates" / "lost_name_review.csv"

# 已有卡名（用于过滤）
KNOWN = set()
for p in (ROOT / "data" / "cards").glob("*.md"):
    KNOWN.add(p.stem.split("_")[0])
# 已在考据表 A 类视为「可并入」的
ALREADY = KNOWN | {
    "刘廙", "辛毗", "刘晔", "刘岱", "刘艾", "杜乔", "荀勖", "孙峻", "刁玄",
    "刘珍", "尹勋", "窦宪", "王辅", "王奇", "傅商", "郑业", "施延", "金迁",
    "许章", "邓义", "梁不疑", "阎畅", "周毖", "金安上", "郑玄",
}

# 明确可猜的
GUESS = {
    "君卿": "侍中君卿（姓佚）",
    "常洽": "常洽",
    "嵩": "嵩（姓佚）",
    "子侯": "霍嬗（子侯）",
}


def main() -> None:
    rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
    out = []
    rid = 0
    for r in rows:
        sent = r.get("sentence") or ""
        label = r.get("anon_label") or ""
        # 已在卡的直接跳过（不占你时间）
        names_in = set(re.findall(r"[一-龥]{2,3}", sent))
        if any(n in ALREADY for n in names_in):
            # 但「侍中X」X不在 ALREADY 的仍留下
            m = re.search(r"侍中([一-龥]{1,3})", sent)
            if not m or m.group(1) in ALREADY:
                continue

        rid += 1
        # 猜名
        guess = ""
        for k, v in GUESS.items():
            if k in sent:
                guess = v
                break
        if not guess:
            m = re.search(r"侍中([一-龥]{1,3})", sent)
            if m:
                guess = m.group(1) + "（待核）"
        if not guess and "拜" in sent:
            m = re.search(r"拜([一-龥]{1,3})侍中", sent)
            if m:
                guess = m.group(1) + "（待核）"

        # 默认 decision
        dec = "无法判断"
        if "君卿" in sent:
            dec = "确认建卡"
            guess = "侍中君卿（姓佚）"
        elif "常洽" in sent:
            dec = "确认建卡"
        elif "嵩" in sent and "侍中" in sent:
            dec = "确认建卡"
            guess = "嵩（姓佚）"
        elif "百官" in r.get("juan", "") or "加官" in sent or "亡員" in sent or "亡员" in sent:
            dec = "制度条"
        elif "持节" in sent or "持節" in sent or "遣侍中" in sent or "使侍中" in sent:
            dec = "无法判断"  # 使职无名

        out.append(
            {
                "row_id": rid,
                "book": r.get("book"),
                "juan": r.get("juan"),
                "sentence": sent[:240],
                "guess_name": guess,
                "decision": dec,
                "canonical_name": "",
                "note": r.get("note", ""),
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["row_id", "book", "juan", "sentence", "guess_name", "decision", "canonical_name", "note"],
        )
        w.writeheader()
        w.writerows(out)
    print("rows", len(out), "->", OUT)
    for r in out:
        print(f"{r['row_id']:02d} [{r['decision']}] {r['guess_name'] or '?'} | {r['sentence'][:80]}")


if __name__ == "__main__":
    main()
