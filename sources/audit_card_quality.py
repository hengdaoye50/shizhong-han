"""审计卡片质量问题：重复 quote、注疏残句、过薄履历。"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"

NOTE_PAT = re.compile(r"（注[:：]|（案[:：]|\{\{|\b注曰|師古曰|師古云")


def parse_sources(fm: str) -> list[tuple[str, str, str]]:
    srcs = []
    cur = None
    for line in fm.splitlines():
        if line.strip().startswith("- book:"):
            if cur:
                srcs.append(tuple(cur))
            cur = [line.split(":", 1)[1].strip(), "", ""]
        elif cur is not None and "juan:" in line:
            cur[1] = line.split(":", 1)[1].strip()
        elif cur is not None and "quote:" in line:
            cur[2] = line.split(":", 1)[1].strip().strip("「」")
    if cur:
        srcs.append(tuple(cur))
    return srcs


def main() -> None:
    stats = Counter()
    problem_cards = []
    for p in sorted(CARDS.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            continue
        fm = m.group(1)
        name_m = re.search(r"^name:\s*(.+)$", fm, re.M)
        name = name_m.group(1).strip() if name_m else p.stem
        srcs = parse_sources(fm)
        quotes = [s[2] for s in srcs]
        # 重复 quote（去空白后）
        norm = [re.sub(r"\s+", "", q) for q in quotes]
        dup = len(norm) - len(set(norm))
        # 注疏
        notes = sum(1 for q in quotes if NOTE_PAT.search(q))
        # 过短/机械
        short = sum(1 for q in quotes if len(q) < 20)
        # nature 重复
        nat = re.findall(r"nature:\s*(.+)", fm)
        nat_dup = len(nat) - len(set(nat))
        if dup or notes or short or len(srcs) > 6:
            stats["flagged"] += 1
            problem_cards.append((name, p.name, len(srcs), dup, notes, short, nat_dup))
        else:
            stats["ok"] += 1
        stats["dup_quotes"] += dup
        stats["note_quotes"] += notes
        stats["short_quotes"] += short

    print(dict(stats))
    print("top problems:")
    for row in problem_cards[:40]:
        print(f"  {row[0][:10]:10} {row[1][:28]:28} n={row[2]} dup={row[3]} note={row[4]} short={row[5]}")
    print("total problem cards", len(problem_cards))


if __name__ == "__main__":
    main()
