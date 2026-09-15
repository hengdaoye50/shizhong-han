"""为高价值人物从 raw 本传提取「含侍中」句，追加到卡片 sources（人工可审）。

只追加：窗口含姓名且含侍中，且不与现有 quote 重复。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import norm_quote, t2s

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CARDS = ROOT / "data" / "cards"

# 优先人物 + 其本传所在书
TARGETS = {
    "霍光": ("漢書", "卷68"),
    "金日磾": ("漢書", "卷68"),
    "金安上": ("漢書", "卷68"),
    "金涉": ("漢書", "卷68"),
    "金敞": ("漢書", "卷68"),
    "卫青": ("漢書", "卷55"),
    "霍去病": ("漢書", "卷55"),
    "窦宪": ("後漢書", None),
    "贾逵": ("後漢書", None),
    "杨秉": ("後漢書", None),
    "杨赐": ("後漢書", None),
    "何进": ("後漢書", None),
    "来历": ("後漢書", None),
    "董允": ("三國志", None),
    "费祎": ("三國志", None),
}


def find_card(name: str) -> Path | None:
    for p in CARDS.glob(f"{name}_*.md"):
        return p
    return None


def extract_sentences(text: str, name: str, max_n: int = 3) -> list[str]:
    out = []
    for m in re.finditer(re.escape(name), text):
        a = max(0, m.start() - 100)
        b = min(len(text), m.end() + 120)
        win = text[a:b]
        if "侍中" not in win:
            continue
        # 粗句切
        parts = re.split(r"[。！？；]", win)
        for part in parts:
            if name in part and "侍中" in part:
                s = t2s(part.strip())
                s = re.sub(r"^\s*[，、]*", "", s)
                if 8 <= len(s) <= 120:
                    out.append(s)
        if len(out) >= max_n:
            break
    # 去重保序
    seen = set()
    uniq = []
    for s in out:
        k = norm_quote(s)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(s)
    return uniq[:max_n]


def main() -> None:
    added_total = 0
    for name, (book, juan_hint) in TARGETS.items():
        card = find_card(name)
        if not card:
            print("no card", name)
            continue
        raw_dir = RAW / book
        if not raw_dir.exists():
            print("no raw", book)
            continue
        # 选卷：优先文件名含卷号
        files = sorted(raw_dir.glob("*.txt"))
        if juan_hint:
            prefer = [f for f in files if juan_hint.replace("卷", "") in f.name or juan_hint in f.name]
            files = prefer + [f for f in files if f not in prefer]

        existing = set()
        t = card.read_text(encoding="utf-8")
        for q in re.findall(r"^\s+quote:\s*(.*)$", t, re.M):
            existing.add(norm_quote(t2s(q)))

        new_quotes = []
        for f in files[:40]:
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if name not in text or "侍中" not in text:
                continue
            for s in extract_sentences(text, name, 2):
                k = norm_quote(s)
                if k in existing:
                    continue
                existing.add(k)
                new_quotes.append((book, f.stem, f"「{s}」"))
            if len(new_quotes) >= 2:
                break

        if not new_quotes:
            print("no new quotes", name)
            continue

        # 插入 sources 块末尾
        m = re.search(r"sources:\n((?:[ \t].*\n)*)", t)
        if not m:
            print("no sources block", name)
            continue
        block = m.group(1)
        add = ""
        for book, juan, quote in new_quotes:
            add += f"  - book: {book}\n    juan: {juan}\n    quote: {quote}\n"
        # 去重后再插
        new_t = t[: m.end()] + add + t[m.end() :]
        card.write_text(new_t, encoding="utf-8")
        added_total += len(new_quotes)
        print(f"+{len(new_quotes)} {name}: {new_quotes[0][2][:50]}")

    print("total quotes added", added_total)


if __name__ == "__main__":
    main()
