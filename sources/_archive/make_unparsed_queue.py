"""导出未解析但含人名线索的句子，供人工捞人。

输出:
  data/candidates/unparsed_namequeue.csv
  列: cand_row, book, juan, sentence, person(待填), status(待审), note
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "data" / "candidates" / "shizhong_candidates.csv"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
OUT = ROOT / "data" / "candidates" / "unparsed_namequeue.csv"

# 与侍中相关的任职/邻接线索
HINT = re.compile(
    r"(为|為|拜|遷|迁|稍遷|稍迁|徵|征|擢|加|入為|入为|復為|复为|再為|再为)侍中"
    r"|侍中(守|領|领|兼|行|知|监|監)"
    r"|侍中[、，][一-龥]{1,4}"
    r"|以[一-龥]{2,4}為侍中|以[一-龥]{2,4}为侍中"
)


def main() -> None:
    rows = list(csv.DictReader(CAND.open(encoding="utf-8-sig")))
    ev = list(csv.DictReader(EV.open(encoding="utf-8-sig")))
    parsed = {int(r["cand_row"]) for r in ev if str(r.get("cand_row", "")).isdigit()}

    out_rows = []
    for i, r in enumerate(rows, start=2):
        if i in parsed:
            continue
        s = (r.get("sentence") or "").strip()
        if not s or "侍中" not in s:
            continue
        if not HINT.search(s):
            continue
        # 排除纯官名列举/百官表行且无人名线索
        out_rows.append(
            {
                "cand_row": i,
                "book": r.get("book"),
                "juan": r.get("juan"),
                "sentence": s[:300],
                "person": "",
                "status": "待审",
                "note": "",
            }
        )

    # 按书排序：两汉优先
    order = {"史記": 0, "漢書": 1, "後漢書": 2, "全漢文": 3, "全後漢文": 4,
             "前漢紀": 5, "後漢紀": 6, "東觀漢記": 7, "隸釋": 8, "隸續": 9,
             "金石錄": 10, "集古錄": 11, "三國志": 12}
    out_rows.sort(key=lambda r: (order.get(r["book"], 99), int(r["cand_row"])))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["cand_row", "book", "juan", "sentence", "person", "status", "note"]
        )
        w.writeheader()
        w.writerows(out_rows)

    from collections import Counter
    print("queue", len(out_rows), "->", OUT)
    print(Counter(r["book"] for r in out_rows).most_common())


if __name__ == "__main__":
    main()
