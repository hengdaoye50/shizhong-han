"""审计 timeline 解析：朝代窗口 vs term 年份，及 nature 可疑触发词。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TL = ROOT / "shizhongdata" / "data" / "timeline.json"
CARDS = ROOT / "data" / "cards"

# 朝代主窗口（与 build_timeline BANDS 一致，宽松重叠）
DYN_OK = {
    "西汉": [(-220, 25)],
    "新": [(-20, 30)],
    "更始": [(18, 30)],
    "东汉": [(20, 230)],
    "汉魏之际": [(170, 240)],
    "魏": [(200, 270)],
    "蜀汉": [(200, 270)],
    "吴": [(200, 290)],
    "晋": [(250, 320)],
    "西汉_新": [(-220, 30)],
    "更始_东汉": [(18, 230)],
    "西汉_东汉": [(-220, 230)],
    "魏_晋": [(200, 320)],
    "蜀汉_魏": [(200, 270)],
    "更始_东汉": [(18, 230)],
}

# nature 里不应被当成纪年的词（出现在否定/说明中时易误触发）
NEG = re.compile(r"非|勿|不作|待考|或系|误|待核|阙疑")
ERA_LIKE = re.compile(
    r"建武|建安|建初|建和|建光|永平|永元|永宁|永兴|永寿|永建|延光|延熹|"
    r"元寿|元兴|元和|章和|阳嘉|熹平|嘉禾|初平|兴平|正始|景初|嘉平|青龙|"
    r"黄初|太和|建平|哀|平间|光武|明帝|章帝|和帝|安帝|顺帝|桓帝|灵帝|"
    r"献帝|武帝|昭帝|宣帝|元帝|成帝|哀帝|平帝|惠帝|吕后|更始|魏国|魏文帝|"
    r"曹爽|王莽|孙权|孙皓|后主|蜀汉|晋侍中"
)


def dyn_ok(dyn: str, y0, y1) -> bool:
    windows = DYN_OK.get(dyn) or DYN_OK.get(dyn.replace("漢", "汉")) or []
    if not windows:
        return True  # 未知朝代不判
    for a, b in windows:
        # term 与窗口有重叠即可
        if y1 is None:
            if a <= y0 <= b:
                return True
        else:
            if y0 <= b and (y1 >= a or y1 is None):
                return True
    return False


def main() -> None:
    t = json.loads(TL.read_text(encoding="utf-8"))
    items = t.get("items") or []
    print("items", len(items), "meta", t.get("meta"))
    flags = []
    for it in items:
        name = it.get("name")
        dyn = it.get("dynasty") or ""
        prec = it.get("precision")
        term = it.get("term") or []
        life = it.get("life")
        nature = it.get("nature") or ""
        reasons = []
        # 1) 朝代窗口
        if term:
            y0 = term[0]
            y1 = term[1] if len(term) > 1 else term[0]
            if not dyn_ok(dyn, y0, y1):
                reasons.append(f"term{term} 不在朝代{dyn}窗口")
        if life and len(life) == 2:
            if not dyn_ok(dyn, life[0], life[1]):
                reasons.append(f"life{life} 不在朝代{dyn}窗口")
        # 2) nature 含否定/待考却仍有 era/exact 年
        if NEG.search(nature) and prec in ("era", "exact"):
            reasons.append(f"precision={prec} 但 nature 含否定/待考词")
        # 3) nature 无纪年词却给出 term
        if term and not ERA_LIKE.search(nature):
            reasons.append(f"有 term{term} 但 nature 无年号/帝号词: {nature[:40]}")
        # 4) exact 但 life 异常
        if prec == "exact" and life:
            if life[0] > life[1]:
                reasons.append(f"life 起止颠倒 {life}")
            if life[0] < -250 or life[1] > 350:
                reasons.append(f"life 超出两汉三国晋 {life}")
        # 5) term 全 0 或空
        if term and all(x == 0 for x in term):
            reasons.append("term 全 0")
        if reasons:
            flags.append((prec, dyn, name, nature[:50], term, life, reasons))

    print("flagged", len(flags))
    for row in sorted(flags, key=lambda x: (x[0] or "", x[2] or "")):
        print("---")
        print(row[0], row[1], row[2])
        print("  nature:", row[3])
        print("  term:", row[4], "life:", row[5])
        for r in row[6]:
            print("  !", r)

    # 附：从卡片 nature 重读，列出含否定词但已上轴的
    print("\n=== cards: nature 含否定/待考 且 timeline 有 term ===")
    by_name = {it.get("name"): it for it in items}
    for p in sorted(CARDS.glob("*.md")):
        raw = p.read_text(encoding="utf-8", errors="ignore")
        name = p.stem.split("_")[0]
        m = re.search(r"^    nature:\s*(.*)$", raw, re.M)
        if not m:
            continue
        nat = m.group(1).strip()
        if not NEG.search(nat):
            continue
        it = by_name.get(name)
        if it and it.get("term"):
            print(name, "prec=", it.get("precision"), "term=", it.get("term"), "|", nat[:70])


if __name__ == "__main__":
    main()
