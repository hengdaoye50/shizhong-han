"""导出全量名录并自检：重复名、朝代异常、证据过薄、可疑卡。"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
OUT = ROOT / "data" / "candidates" / "full_roster_audit.csv"


def parse_card(p: Path) -> dict:
    text = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {"file": p.name, "error": "no frontmatter"}
    fm = m.group(1)

    def grab(k: str) -> str:
        mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
        return mm.group(1).strip() if mm else ""

    n_quotes = len(re.findall(r"-\s*book:", fm))
    n_bio = len(re.findall(r"^\d+\. ", text, re.M))
    has_rel = "| " in text.split("## 关系")[-1] if "## 关系" in text else False
    return {
        "file": p.name,
        "id": grab("id"),
        "name": grab("name"),
        "style_name": grab("style_name"),
        "dynasty": grab("dynasty"),
        "status": grab("status"),
        "category": grab("category"),
        "n_quotes": n_quotes,
        "n_bio": n_bio,
        "has_rel": has_rel,
        "bytes": p.stat().st_size,
    }


def main() -> None:
    ev_count = Counter()
    if EV.exists():
        with EV.open(encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                ev_count[r["person"]] += 1

    rows = []
    name_files = defaultdict(list)
    for p in sorted(CARDS.glob("*.md")):
        r = parse_card(p)
        r["n_evidence_csv"] = ev_count.get(r.get("name", ""), 0)
        rows.append(r)
        name_files[r.get("name", p.stem)].append(p.name)

    # 疑点
    issues = []
    for r in rows:
        flags = []
        if r.get("error"):
            flags.append("NO_FM")
        if r.get("n_quotes", 0) == 0:
            flags.append("NO_QUOTE")
        if r.get("n_bio", 0) == 0:
            flags.append("NO_BIO")
        if r.get("n_evidence_csv", 0) == 0 and r.get("n_quotes", 0) <= 1:
            flags.append("THIN")
        if r.get("dynasty", "") in ("兩漢", "两汉", ""):
            flags.append("DYN_VAGUE")
        if r.get("status") == "草稿" and r.get("n_quotes", 0) < 2:
            flags.append("DRAFT_THIN")
        # 名过短或含可疑
        nm = r.get("name") or ""
        if len(nm) < 2:
            flags.append("NAME_SHORT")
        if nm in {"某璩", "被表者待考", "佚名侍中（禁中出入）"}:
            flags.append("PLACEHOLDER")
        if "阙" == (r.get("style_name") or "") and r.get("n_quotes", 0) < 2:
            flags.append("WEAK")
        r["flags"] = "|".join(flags)

    dup_names = [n for n, fs in name_files.items() if len(fs) > 1]
    print("cards", len(rows))
    print("duplicate names", dup_names)
    print("dynasty", Counter(r.get("dynasty") for r in rows))
    print("status", Counter(r.get("status") for r in rows))
    flag_c = Counter()
    for r in rows:
        for f in (r["flags"] or "").split("|"):
            if f:
                flag_c[f] += 1
    print("flags", flag_c)

    print("\n--- flagged ---")
    for r in rows:
        if r["flags"]:
            print(f"{r.get('id','?'):6} {r.get('name','?'):12} {r.get('dynasty','?'):10} q={r.get('n_quotes',0)} ev={r.get('n_evidence_csv',0)} {r['flags']}")

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["id", "name", "style_name", "dynasty", "status", "category", "n_quotes", "n_bio", "n_evidence_csv", "flags", "file"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("->", OUT)


if __name__ == "__main__":
    main()
