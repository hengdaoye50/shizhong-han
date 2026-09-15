"""全量清洗人物卡：

1. quote 去注疏（（注：…）、（案：…）、{{…}}）
2. quote 去重（归一空白后）
3. 去掉过短碎片（<12字且无「侍中」）
4. 合并相同 nature 的 shizhong_terms
5. 重建 SQLite source/term
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"

# 注疏模式
NOTE_RES = [
    re.compile(r"（注[:：][^）]*）"),
    re.compile(r"（案[:：][^）]*）"),
    re.compile(r"\{\{[^}]*\}\}"),
    re.compile(r"（一作[^）]*）"),
    re.compile(r"（集解[^）]*）"),
    re.compile(r"\[\[|\]\]"),
]


def clean_quote(q: str) -> str:
    q = q.strip().strip("「」")
    for pat in NOTE_RES:
        q = pat.sub("", q)
    q = re.sub(r"\s+", "", q)
    # 去尾部残句标点堆叠
    q = re.sub(r"[。，、；：]+$", "", q)
    return q


def is_useful(q: str) -> bool:
    if len(q) < 12:
        return False
    # 至少含侍中或与任职/关系相关
    keys = ("侍中", "遷", "迁", "拜", "為", "为", "字", "侯", "將軍", "将军", "尚書", "尚书")
    return any(k in q for k in keys) or len(q) >= 24


def parse_card(text: str) -> dict | None:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return None
    fm, body = m.group(1), m.group(2)
    meta = {}
    for k in ("id", "name", "style_name", "dynasty", "status", "category", "origin", "birth", "death"):
        mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
        meta[k] = mm.group(1).strip() if mm else ""

    # terms
    terms = []
    in_t = False
    cur = None
    for line in fm.splitlines():
        if line.startswith("shizhong_terms:"):
            in_t = True
            continue
        if in_t:
            if line and not line[0].isspace() and not line.strip().startswith("-"):
                in_t = False
            else:
                s = line.strip()
                if s.startswith("- start:"):
                    if cur:
                        terms.append(cur)
                    cur = {"start": s.split(":", 1)[1].strip(), "end": "", "nature": "", "evidence": ""}
                elif cur is not None and s.startswith("end:"):
                    cur["end"] = s.split(":", 1)[1].strip()
                elif cur is not None and s.startswith("nature:"):
                    cur["nature"] = s.split(":", 1)[1].strip()
                elif cur is not None and s.startswith("evidence:"):
                    cur["evidence"] = s.split(":", 1)[1].strip()
    if cur:
        terms.append(cur)

    # sources
    srcs = []
    in_s = False
    cur_s = None
    for line in fm.splitlines():
        if line.startswith("sources:"):
            in_s = True
            continue
        if in_s:
            if line and not line[0].isspace() and not line.strip().startswith("-"):
                in_s = False
            else:
                if line.strip().startswith("- book:"):
                    if cur_s:
                        srcs.append(cur_s)
                    cur_s = {"book": line.split(":", 1)[1].strip(), "juan": "", "quote": ""}
                elif cur_s is not None and "juan:" in line:
                    cur_s["juan"] = line.split(":", 1)[1].strip()
                elif cur_s is not None and "quote:" in line:
                    cur_s["quote"] = line.split(":", 1)[1].strip()
    if cur_s:
        srcs.append(cur_s)
    return {"meta": meta, "terms": terms, "srcs": srcs, "body": body}


def dedupe_terms(terms: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for t in terms:
        key = (t.get("start", ""), t.get("end", ""), t.get("nature", "")[:40])
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out or terms[:1]


def rebuild_fm(meta: dict, terms: list[dict], srcs: list[dict]) -> str:
    lines = ["---"]
    for k in ("id", "name", "style_name", "dynasty", "status", "category", "origin", "birth", "death"):
        lines.append(f"{k}: {meta.get(k, '')}")
    lines.append("shizhong_terms:")
    for t in terms:
        lines.append(f"  - start: {t.get('start') or '阙'}")
        lines.append(f"    end: {t.get('end') or '阙'}")
        lines.append(f"    nature: {t.get('nature') or '阙'}")
        lines.append(f"    evidence: {t.get('evidence') or '有明文'}")
    lines.append("sources:")
    if not srcs:
        lines.append("  - book: 阙")
        lines.append("    juan: 阙")
        lines.append("    quote: 「阙」")
    else:
        for s in srcs:
            lines.append(f"  - book: {s['book']}")
            lines.append(f"    juan: {s['juan']}")
            lines.append(f"    quote: 「{s['quote']}」")
    lines.append("---")
    return "\n".join(lines)


def main() -> None:
    n_card = n_q_in = n_q_out = n_note = 0
    for p in sorted(CARDS.glob("*.md")):
        parsed = parse_card(p.read_text(encoding="utf-8"))
        if not parsed:
            continue
        n_card += 1
        new_srcs = []
        seen = set()
        for s in parsed["srcs"]:
            n_q_in += 1
            q = clean_quote(s.get("quote", ""))
            if "（注" in s.get("quote", "") or "（案" in s.get("quote", ""):
                n_note += 1
            if not is_useful(q):
                continue
            key = q[:50]
            if key in seen:
                continue
            seen.add(key)
            new_srcs.append({"book": s.get("book") or "阙", "juan": s.get("juan") or "阙", "quote": q})
            n_q_out += 1
        terms = dedupe_terms(parsed["terms"])
        fm = rebuild_fm(parsed["meta"], terms, new_srcs)
        p.write_text(fm + "\n" + parsed["body"].lstrip("\n"), encoding="utf-8")

    # 重建 source/term
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM shizhong_term")
    cur.execute("DELETE FROM source")
    for p in sorted(CARDS.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        parsed = parse_card(text)
        if not parsed:
            continue
        pid = parsed["meta"].get("id")
        for s in parsed["srcs"]:
            if s["book"] == "阙":
                continue
            cur.execute(
                "INSERT INTO source (book,juan,quote,path) VALUES (?,?,?,?)",
                (s["book"], s["juan"], s["quote"][:500], p.name),
            )
            sid = cur.lastrowid
            for t in parsed["terms"]:
                cur.execute(
                    """INSERT OR IGNORE INTO shizhong_term
                    (person_id,start_ym,end_ym,nature,evidence,source_id,start_year,end_year,nature_primary)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        pid,
                        t.get("start") or "阙",
                        t.get("end") or "阙",
                        (t.get("nature") or "阙")[:120],
                        t.get("evidence") or "有明文",
                        sid,
                        None,
                        None,
                        "其他",
                    ),
                )
    con.commit()
    cur.execute("SELECT COUNT(*) FROM source")
    print("source", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM shizhong_term")
    print("term", cur.fetchone()[0])
    con.close()
    print(f"cards={n_card} quotes_in={n_q_in} quotes_out={n_q_out} stripped_notes={n_note}")


if __name__ == "__main__":
    main()
