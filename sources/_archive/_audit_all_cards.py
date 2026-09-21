"""全量人物卡质量审计：抽取误读与名实不符风险。"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS = ROOT / "data" / "cards"

# 可疑名：占位、含待考/阙、过短、像官职/动词短语
PLACEHOLDER = re.compile(r"待考|阙|佚名|某|占位|制度")
# 名过短或含非人名结构
SUS_NAME = re.compile(r"[（(]|之|为|侍中|将军|太守|校尉|大夫|侯|嗣|免|死")
# 明显不是人名的抽句残片（对照历史误抽）
FRAG = re.compile(
    r"^(光中为|再迁为|三迁为|上使|将军素|将军青|和帝时|灵帝时|二千石|"
    r"诸曹|后为|官至|拜劭为|子璜为|与严助|卿大夫|上拜涉|涉为|涉爲|"
    r"延光中|卯延光中|帝时为|禄大夫|马都尉|为卫尉)$"
)
NEG = re.compile(r"非|勿|待考|阙疑|不作定说|误|待核")


def parse_card(p: Path) -> dict | None:
    t = p.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S)
    if not m:
        return None
    fm, body = m.group(1), m.group(2)

    def grab(k: str) -> str:
        mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
        return mm.group(1).strip() if mm else ""

    quotes = re.findall(r"quote:\s*(.+)", fm)
    nature = ""
    nm = re.search(r"^    nature:\s*(.*)$", fm, re.M)
    if nm:
        nature = nm.group(1).strip()
    name = grab("name")
    return {
        "file": p.name,
        "id": grab("id"),
        "name": name,
        "dynasty": grab("dynasty"),
        "status": grab("status"),
        "nature": nature,
        "quotes": quotes,
        "bio": body,
        "origin": grab("origin"),
        "category": grab("category"),
    }


def name_in_text(name: str, text: str) -> bool:
    if not name:
        return False
    # 全名或去「待考」后的主名
    base = re.sub(r"[（(].*?[)）]", "", name).strip()
    if base and base in text:
        return True
    # 单字名且文本中高频易误——不单凭单字判命中
    return False


def main() -> None:
    cards = []
    for p in sorted(CARDS.glob("*.md")):
        c = parse_card(p)
        if c:
            cards.append(c)
    print("cards", len(cards))

    flags: list[tuple[str, list[str]]] = []
    name_to_files = defaultdict(list)
    for c in cards:
        name_to_files[c["name"]].append(c["file"])
        reasons = []
        name = c["name"]
        # 1) 名可疑
        if PLACEHOLDER.search(name):
            reasons.append(f"名含占位/待考: {name}")
        if SUS_NAME.search(name):
            reasons.append(f"名含非人名结构: {name}")
        if FRAG.match(name):
            reasons.append(f"名疑为抽句残片: {name}")
        if len(re.sub(r"[（(].*?[)）]", "", name).strip()) == 1 and "待考" not in name:
            reasons.append(f"单字名: {name}")
        # 2) 全部引文都不含姓名
        qs = c["quotes"]
        if qs:
            hit = any(name_in_text(name, q) for q in qs)
            base = re.sub(r"[（(].*?[)）]", "", name).strip()
            # 亦检查单字主名出现在 quote（仅当 base 长度>=2）
            if not hit and len(base) >= 2:
                # 宽松：任一 quote 含 base 前2字
                hit = any(base[:2] in q for q in qs)
            if not hit:
                reasons.append(f"{len(qs)}条引文均未见姓名「{name}」")
        else:
            reasons.append("无 sources quote")
        # 3) nature 含否定/待考
        if NEG.search(c["nature"]):
            reasons.append(f"nature 含否定/待考: {c['nature'][:40]}")
        # 4) 状态异常
        if c["status"] and ("废止" in c["status"] or "待审" in c["status"]):
            reasons.append(f"status={c['status']}")
        # 5) 生平待补且引文也弱
        bio = c["bio"]
        if "（待补）" in bio[:80] and len(re.sub(r"\s", "", bio)) < 50:
            reasons.append("生平仍为待补占位")
        if reasons:
            flags.append((c["file"], reasons))

    print("flagged", len(flags))
    for f, reasons in flags:
        print("---", f)
        for r in reasons:
            print("  !", r)

    # 同名多人
    print("\n=== duplicate name fields ===")
    for n, files in name_to_files.items():
        if n and len(files) > 1:
            print(n, files)

    # 姓名出现在多卡 quote 且本卡名不在 quote——抽查
    print("\n=== card name missing from all quotes (strict) ===")
    for c in cards:
        name = c["name"]
        base = re.sub(r"[（(].*?[)）]", "", name).strip()
        if len(base) < 2:
            continue
        qs = c["quotes"]
        if not qs:
            continue
        if not any(name_in_text(name, q) or base in q or base[:2] in q for q in qs):
            print(c["file"], name, "dyn=", c["dynasty"], "|", (qs[0] if qs else "")[:70])


if __name__ == "__main__":
    main()
