"""汇总卡片中标「待考/阙疑/待核/不作定说」的条目，供人工审定。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS = ROOT / "data" / "cards"
FLAG = re.compile(r"待考|阙疑|待核|不作定说|系连待考|任职待考|名不全|占位|勿用|误挂|已剔除")


def parse(p: Path):
    t = p.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S)
    if not m:
        return None
    fm, body = m.group(1), m.group(2)

    def grab(k):
        mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
        return mm.group(1).strip() if mm else ""

    nature = ""
    nm = re.search(r"^    nature:\s*(.*)$", fm, re.M)
    if nm:
        nature = nm.group(1).strip()
    quotes = re.findall(r"quote:\s*(.+)", fm)
    notes = []
    if "## 校录备注" in body:
        sec = re.split(r"## 校录备注\n", body, maxsplit=1)[-1]
        for ln in sec.splitlines():
            s = ln.strip()
            if s.startswith("-") or s.startswith("*"):
                notes.append(s.lstrip("-* ").strip())
            elif s and not s.startswith("#"):
                if FLAG.search(s):
                    notes.append(s.strip())
    bio_hits = [ln.strip() for ln in body.splitlines() if FLAG.search(ln)]
    return {
        "file": p.name,
        "id": grab("id"),
        "name": grab("name"),
        "dynasty": grab("dynasty"),
        "status": grab("status"),
        "category": grab("category"),
        "nature": nature,
        "quotes": quotes,
        "notes": notes,
        "bio_hits": bio_hits,
    }


def main():
    rows = []
    for p in sorted(CARDS.glob("*.md")):
        c = parse(p)
        if not c:
            continue
        reasons = []
        if FLAG.search(c["nature"] or ""):
            reasons.append(f"nature: {c['nature']}")
        if FLAG.search(c["status"] or ""):
            reasons.append(f"status: {c['status']}")
        if FLAG.search(c["name"] or ""):
            reasons.append(f"name: {c['name']}")
        for n in c["notes"]:
            if FLAG.search(n):
                reasons.append(f"备注: {n}")
        for b in c["bio_hits"]:
            if FLAG.search(b):
                reasons.append(f"生平: {b[:80]}")
        if not reasons:
            continue
        rows.append({**c, "reasons": reasons})

    print("COUNT", len(rows))
    print()
    for c in rows:
        print("=" * 60)
        print(f"{c['id']} | {c['name']} | {c['dynasty']} | {c['file']}")
        print(f"status={c['status']} category={c['category']}")
        print(f"nature: {c['nature']}")
        for r in c["reasons"]:
            print(f"  ! {r}")
        if c["quotes"]:
            print("  quotes:")
            for q in c["quotes"][:3]:
                print(f"    · {q[:100]}")
        else:
            print("  quotes: （无）")

    out = ROOT / "data" / "candidates" / "daikao_review.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nWROTE", out, "n=", len(rows))


if __name__ == "__main__":
    main()
