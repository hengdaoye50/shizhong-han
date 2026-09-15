"""把 vendors/kanripo-* 的 txt 卷导入 data/raw/。

Kanripo 文件为 UTF-8，含 mandoku 元信息头，正文自 #+ 之后或首行 pb 标记起。

用法:
  python sources/import_kanripo.py
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendors"
OUT = ROOT / "data" / "raw"

# 目录名 -> 规范书名
BOOKS = {
    "kanripo-KR2n0017": "隸釋",
    "kanripo-KR2n0018": "隸續",
    "kanripo-KR2d0002": "東觀漢記",
    "kanripo-KR2b0003": "前漢紀",
    "kanripo-KR2b0004": "後漢紀",
    "kanripo-KR2n0012": "集古錄",
    "kanripo-KR2n0013": "金石錄",
}


def clean(text: str) -> str:
    # 去 mandoku 头与标记
    lines = []
    for line in text.splitlines():
        if line.startswith("#") or line.startswith("-*-"):
            continue
        line = re.sub(r"<pb:[^>]+>", "", line)
        line = re.sub(r"<折[^>]*/?>", "", line)
        line = re.sub(r"<[^>]+>", "", line)
        lines.append(line)
    body = "\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip() + "\n"


def main() -> None:
    total = 0
    for folder, book in BOOKS.items():
        src = VENDOR / folder
        if not src.is_dir():
            print(f"skip missing {src}")
            continue
        dest = OUT / book
        dest.mkdir(parents=True, exist_ok=True)
        n = 0
        for p in sorted(src.glob("*.txt")):
            # KR2n0017_001.txt -> 卷001.txt
            m = re.search(r"_(\d+)\.txt$", p.name)
            name = f"卷{m.group(1)}.txt" if m else p.name
            (dest / name).write_text(clean(p.read_text(encoding="utf-8")), encoding="utf-8")
            n += 1
        print(f"{folder} -> {book}: {n}")
        total += n
    print("total", total)


if __name__ == "__main__":
    main()
