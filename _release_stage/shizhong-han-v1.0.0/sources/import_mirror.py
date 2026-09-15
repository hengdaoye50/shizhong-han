"""把 vendors/china-history 的 *-原文.html 转成 data/raw/mirror 下的纯文本。

用法:
  python sources/import_mirror.py
  python sources/import_mirror.py --book 汉书
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendors" / "china-history"
OUT = ROOT / "data" / "raw" / "mirror"

BOOKS = {
    "汉书": "漢書",
    "后汉书": "後漢書",
    "史记": "史記",
    "三国志": "三國志",
}

SKIP_TAGS = {"script", "style", "noscript"}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self._skip += 1
        if tag in {"p", "div", "br", "tr", "h1", "h2", "h3", "h4", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        t = data.strip()
        if t:
            self.parts.append(t)

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n\n", raw)
        return raw.strip() + "\n"


def html_to_text(html: str) -> str:
    p = TextExtractor()
    p.feed(html)
    return p.text()


def import_book(src_name: str) -> int:
    src = VENDOR / src_name
    if not src.is_dir():
        print(f"missing {src}", file=sys.stderr)
        return 0
    dest_root = OUT / BOOKS.get(src_name, src_name)
    n = 0
    for html_path in sorted(src.rglob("*原文*.html")):
        rel = html_path.relative_to(src)
        dest = dest_root / rel.with_suffix(".txt")
        # 第X章-篇名-原文.html -> 第X章-篇名.txt
        dest = dest.with_name(dest.name.replace("-原文", ""))
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = html_to_text(html_path.read_text(encoding="utf-8", errors="replace"))
        dest.write_text(text, encoding="utf-8")
        n += 1
    print(f"{src_name} -> {dest_root}: {n} files")
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", choices=list(BOOKS), help="只转某一书")
    args = ap.parse_args()
    names = [args.book] if args.book else list(BOOKS)
    total = 0
    for name in names:
        total += import_book(name)
    print(f"done total={total}")


if __name__ == "__main__":
    main()
