"""应用 persons_review.csv 的人工审读，重建证据、索引与卡片。

支持 decision 形态:
  留 | 删 | 错误 | 并 <名> | 改 <名>[、名2...] | 存疑 | 无法判断 | 留 <名>
"""

from __future__ import annotations

import csv
import re
import shutil
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "data" / "candidates" / "persons_review.csv"
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
IDX = ROOT / "data" / "candidates" / "persons_index.csv"
KEEP_LIST = ROOT / "data" / "candidates" / "persons_canonical.csv"
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"
BACKUP = ROOT / "data" / "cards" / "_backup_prereview"


def load_review() -> dict[str, dict]:
    raw = REVIEW.read_bytes()
    for enc in ("utf-8-sig", "gb18030", "utf-8"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise SystemExit("cannot decode review csv")
    rows = list(csv.DictReader(text.splitlines()))
    out: dict[str, dict] = {}
    for r in rows:
        person = (r.get("person") or "").strip()
        if not person:
            continue
        dec = (r.get("decision") or "").strip()
        out[person] = {
            "decision": dec,
            "merge_into": (r.get("merge_into") or "").strip(),
            "note": (r.get("note") or "").strip(),
            "n": int(r.get("n_evidence") or 0),
        }
    return out


def parse_decision(dec: str) -> tuple[str, list[str]]:
    """返回 (action, targets). action: keep|drop|rename|merge|uncertain"""
    d = dec.strip()
    if not d or d in {"留"}:
        return "keep", []
    if d.startswith("留"):
        # 留 邓义 / 留 王闳
        rest = d[1:].strip()
        if rest:
            return "rename", [rest]
        return "keep", []
    if d in {"删", "错误", "无法判断"}:
        # 无法判断先 drop 出正式名单，另表
        return "drop", []
    if d == "存疑":
        return "uncertain", []
    if d.startswith("并"):
        rest = d[1:].strip(" 　")
        if not rest and False:
            pass
        targets = [t.strip() for t in re.split(r"[、,，]", rest) if t.strip()]
        return "merge", targets
    if d.startswith("改"):
        rest = d[1:].strip(" 　")
        targets = [t.strip() for t in re.split(r"[、,，]", rest) if t.strip()]
        if not targets:
            return "uncertain", []
        return "rename", targets
    # 未知
    return "uncertain", []


def load_evidence() -> dict[str, list[dict]]:
    bucket: dict[str, list[dict]] = defaultdict(list)
    with EV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            bucket[r["person"]].append(r)
    return bucket


def guess_dynasty(books: list[str]) -> str:
    b = "|".join(books)
    if "三國" in b and not any(x in b for x in ("後漢", "漢書", "史記")):
        return "漢魏之際"
    if any(x in b for x in ("後漢", "后汉", "全後漢")):
        return "東漢"
    if any(x in b for x in ("漢書", "史記", "全漢文", "前漢紀")):
        return "西漢"
    return "兩漢"


def main() -> None:
    review = load_review()
    bucket = load_evidence()
    print("raw persons", len(bucket), "review", len(review))

    canonical: dict[str, list[dict]] = defaultdict(list)
    uncertain: dict[str, list[dict]] = defaultdict(list)
    log: list[str] = []

    for person, evs in bucket.items():
        info = review.get(person)
        if not info:
            # 未出现在审读表：默认 drop（机械抽取残留）
            log.append(f"unreviewed drop {person} ({len(evs)})")
            continue
        action, targets = parse_decision(info["decision"])
        if action == "keep":
            canonical[person].extend(evs)
        elif action == "drop":
            log.append(f"drop {person} ({len(evs)}) {info['note']}")
        elif action == "uncertain":
            uncertain[person].extend(evs)
            log.append(f"uncertain {person} ({len(evs)})")
        elif action in {"rename", "merge"}:
            # 多名：证据挂到第一个，其余作别名记 note
            main_name = targets[0]
            extra = targets[1:] if len(targets) > 1 else []
            for e in evs:
                e = dict(e)
                if extra:
                    e["alias_in_sentence"] = "、".join(extra)
                canonical[main_name].extend([e])
            log.append(f"{action} {person} -> {targets}")
        else:
            uncertain[person].extend(evs)

    # 若 review 里 merge_into 有值且 decision 不是并，也尊重
    # 输出
    print("canonical", len(canonical), "uncertain", len(uncertain))
    for line in log:
        if line.startswith("rename") or line.startswith("merge") or line.startswith("drop"):
            print(" ", line)

    # 写 canonical csv
    with KEEP_LIST.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["person", "n_evidence", "books", "sample", "aliases"],
        )
        w.writeheader()
        for person, evs in sorted(canonical.items(), key=lambda x: -len(x[1])):
            aliases = sorted(
                {e.get("alias_in_sentence") for e in evs if e.get("alias_in_sentence")}
            )
            w.writerow(
                {
                    "person": person,
                    "n_evidence": len(evs),
                    "books": "|".join(sorted({e["book"] for e in evs})),
                    "sample": (evs[0].get("sentence") or "")[:140],
                    "aliases": "、".join(aliases),
                }
            )

    with EV.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["person", "cand_row", "book", "juan", "sentence", "source_file", "alias_in_sentence"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for person, evs in canonical.items():
            for e in evs:
                row = dict(e)
                row["person"] = person
                w.writerow(row)

    # uncertain 单独表
    unc_path = ROOT / "data" / "candidates" / "persons_uncertain.csv"
    with unc_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["person", "n_evidence", "sample", "note"])
        w.writeheader()
        for person, evs in sorted(uncertain.items(), key=lambda x: -len(x[1])):
            w.writerow(
                {
                    "person": person,
                    "n_evidence": len(evs),
                    "sample": (evs[0].get("sentence") or "")[:140],
                    "note": review.get(person, {}).get("note", ""),
                }
            )

    # 重建卡片（骨架，详卡另做）
    if not BACKUP.exists():
        shutil.copytree(CARDS, BACKUP, dirs_exist_ok=True)
    for p in CARDS.glob("*.md"):
        p.unlink()
    used = set()
    for person, evs in sorted(canonical.items(), key=lambda x: -len(x[1])):
        books = sorted({e["book"] for e in evs})
        dyn = guess_dynasty(books)
        i = 1
        while f"P{i:04d}" in used:
            i += 1
        pid = f"P{i:04d}"
        used.add(pid)
        srcs = []
        seen = set()
        for e in evs:
            q = (e.get("sentence") or "").replace('"', "'")[:240]
            if q[:40] in seen:
                continue
            seen.add(q[:40])
            srcs.append(f'  - book: {e.get("book")}\n    juan: {e.get("juan")}\n    quote: 「{q}」')
            if len(srcs) >= 10:
                break
        body = f"""---
id: {pid}
name: {person}
style_name: 阙
dynasty: {dyn}
status: 待审
category: 阙
origin: 阙
birth: 阙
death: 阙
shizhong_terms:
  - start: 阙
    end: 阙
    nature: 阙
    evidence: 有明文
sources:
{chr(10).join(srcs) if srcs else '  - book: 阙'}
---

## 生平履历

（审读后骨架；待语义扩写与联网核对）

## 侍中任职前后

（待校）

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
|  |  |  |  |

## 校录备注

- 审读后规范名；evidence={len(evs)}
- 书目：{'/'.join(books)}
- 校录人/日期：待填
"""
        (CARDS / f"{person}_{dyn}.md").write_text(body, encoding="utf-8")

    # 入库
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM shizhong_term")
    cur.execute("DELETE FROM source")
    cur.execute("DELETE FROM person")
    for p in sorted(CARDS.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            continue
        fm = m.group(1)

        def grab(k: str) -> str:
            mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
            return mm.group(1).strip() if mm else ""

        pid = grab("id")
        cur.execute(
            """INSERT OR REPLACE INTO person
            (id,name,style_name,dynasty,category,origin,birth,death,status,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, grab("name"), grab("style_name"), grab("dynasty"), grab("category"),
                grab("origin"), grab("birth"), grab("death"), grab("status") or "待审", p.name,
            ),
        )
        for sm in re.finditer(r"-\s*book:\s*(.+)\n\s*juan:\s*(.+)\n\s*quote:\s*(.+)", fm):
            book, juan, quote = sm.group(1).strip(), sm.group(2).strip(), sm.group(3).strip().strip("「」")
            if book == "阙":
                continue
            cur.execute(
                "INSERT INTO source (book,juan,quote,path) VALUES (?,?,?,?)",
                (book, juan, quote, p.name),
            )
            cur.execute(
                """INSERT OR IGNORE INTO shizhong_term
                (person_id,start_ym,end_ym,nature,evidence,source_id)
                VALUES (?,?,?,?,?,?)""",
                (pid, "阙", "阙", "阙", "有明文", cur.lastrowid),
            )
    con.commit()
    for t in ("person", "source", "shizhong_term", "relation", "candidate"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(t, cur.fetchone()[0])
    con.close()
    print("canonical csv", KEEP_LIST)
    print("uncertain csv", unc_path)
    print("cards", len(list(CARDS.glob("*.md"))))


if __name__ == "__main__":
    main()
