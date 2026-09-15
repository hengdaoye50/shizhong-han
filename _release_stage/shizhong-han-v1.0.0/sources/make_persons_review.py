"""生成人名审读表：data/candidates/persons_review.csv

列：person, n_evidence, books, sample1, sample2, decision, merge_into, note
decision: 留 | 删 | 并  （并 时在 merge_into 填规范名）
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
OUT = ROOT / "data" / "candidates" / "persons_review.csv"


def main() -> None:
    bucket: dict[str, list[dict]] = defaultdict(list)
    with EV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            bucket[r["person"]].append(r)

    rows = []
    for person, evs in sorted(bucket.items(), key=lambda x: (-len(x[1]), x[0])):
        samples = []
        seen = set()
        for e in evs:
            s = (e.get("sentence") or "").replace("\n", " ")[:160]
            if s[:40] in seen:
                continue
            seen.add(s[:40])
            samples.append(s)
            if len(samples) >= 2:
                break
        while len(samples) < 2:
            samples.append("")
        rows.append(
            {
                "person": person,
                "n_evidence": len(evs),
                "books": "|".join(sorted({e.get("book") or "" for e in evs})),
                "sample1": samples[0],
                "sample2": samples[1],
                "decision": "留",  # 默认，请改 删/并
                "merge_into": "",
                "note": "",
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "person",
                "n_evidence",
                "books",
                "sample1",
                "sample2",
                "decision",
                "merge_into",
                "note",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    print(f"rows={len(rows)} -> {OUT}")


if __name__ == "__main__":
    main()
