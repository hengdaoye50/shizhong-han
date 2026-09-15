"""列出 mirror 中尚未专扫的两汉列传（含侍中句的优先）。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / "data" / "raw" / "mirror"

# 已重点扫过的关键词
DONE_KEYS = [
    "霍光金日", "张汤", "王商史丹", "佞幸", "儒林", "党锢", "文苑", "独行",
    "方术", "循吏", "酷吏", "宦者", "皇后", "张曹郑", "郑范陈贾",
]


def main() -> None:
    for book in ["漢書", "後漢書", "史記", "三國志"]:
        base = MIRROR / book
        if not base.exists():
            print("no", book)
            continue
        files = sorted(base.rglob("*原文*.txt")) + sorted(base.rglob("*.txt"))
        files = sorted(set(files))
        print(f"\n======== {book} ({len(files)}) ========")
        with_sz = 0
        for fp in files:
            try:
                t = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "侍中" not in t:
                continue
            with_sz += 1
            name = fp.name
            marked = any(k in name for k in DONE_KEYS)
            n = t.count("侍中")
            flag = "DONE" if marked else "TODO"
            print(f"  [{flag}] {n:3d}  {name[:50]}")
        print(f"  with 侍中: {with_sz}")


if __name__ == "__main__":
    main()
