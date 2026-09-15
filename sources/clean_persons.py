"""人名规范化：繁简合并、截断纠正、重建卡片与库。

规则:
1. 显式繁简对照表
2. 截断：若 A 是 B 的前缀且 B 证据更多，则 A 并入 B（如 金安 → 金安上）
3. 不自动合并「仅一字之差」的疑似同名，除非在表中

用法:
  python sources/clean_persons.py
"""

from __future__ import annotations

import csv
import re
import shutil
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "data" / "candidates" / "persons_evidence.csv"
IDX = ROOT / "data" / "candidates" / "persons_index.csv"
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"
BACKUP = ROOT / "data" / "cards" / "_backup_preclean"

# 显式繁简 / 异写（canonical 用简体，与 pilot 标注一致）
EXPLICIT = {
    "杜喬": "杜乔",
    "周廣": "周广",
    "劉曄": "刘晔",
    "刘曄": "刘晔",
    "許舜": "许舜",
    "馬宇": "马宇",
    "張辟彊": "张辟强",
    "張辟疆": "张辟强",
    "賈逵": "贾逵",
    "竇憲": "窦宪",
    "劉瑜": "刘瑜",
    "尹勳": "尹勋",
    "魯丕": "鲁丕",
    "梁不疑": "梁不疑",
    "陳羣": "陈群",
    "諸葛瞻": "诸葛瞻",
    "郭攸之": "郭攸之",
    "孫峻": "孙峻",
    "張紹": "张绍",
    "馬良": "马良",
    "許允": "许允",
    "何晏": "何晏",
    "王沈": "王沈",
    "劉廙": "刘廙",
    "劉岱": "刘岱",
    "虞子和": "虞子和",
    "王林卿": "王林卿",
    "劉艾": "刘艾",
    "周毖": "周毖",
    "耿紀": "耿纪",
    "謝惲": "谢惲",
    "伍瓊": "伍琼",
    "鄧義": "邓义",
    "荀勗": "荀勖",
    "王曠": "王旷",
    "鄭業": "郑业",
    "李禎": "李祯",
    "董允書": "董允",
    "董允书": "董允",
    "杜喬奏": "杜乔",
    "杜喬深": "杜乔",
    "杜輔": "杜辅",
    "張辟彊": "张辟强",
    "賈逵": "贾逵",
    "賈逵荐": "贾逵",
}

# 证据中误吞的尾巴（清洗后再若仍以这些结尾且不在白名单，则丢弃该伪名）
GARBAGE_SUFFIX = (
    "书", "書", "奏", "深", "城", "也", "口", "白", "欲", "荐", "薦",
    "慕", "等", "出", "入", "为", "為", "并", "並", "及", "与", "與",
    "上", "下", "代", "安", "将", "將", "自", "乃", "遂", "因", "复", "復",
    "再", "更", "皆", "咸", "称", "稱", "言", "云", "曰", "对", "對",
)

# 截断黑名单：这些短名不得当独立人（必须并入长名）
# 用户明确：金安 只是 金安上 的误截
FORCE_MERGE_INTO = {
    "金安": "金安上",
}


def load_evidence() -> dict[str, list[dict]]:
    bucket: dict[str, list[dict]] = defaultdict(list)
    with EV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            bucket[r["person"]].append(r)
    return bucket


def normalize_bucket(bucket: dict[str, list[dict]]) -> tuple[dict[str, list[dict]], list[str]]:
    log: list[str] = []
    # 1) 显式表
    new: dict[str, list[dict]] = defaultdict(list)
    for person, evs in bucket.items():
        target = EXPLICIT.get(person, person)
        if target != person:
            log.append(f"map {person} -> {target}")
        new[target].extend(evs)
    # 2) 强制截断
    for short, long_ in FORCE_MERGE_INTO.items():
        if short in new:
            log.append(f"force {short} -> {long_} ({len(new[short])} ev)")
            new[long_].extend(new.pop(short))
    # 3) 丢弃明显误截伪名
    drop = []
    for name in list(new.keys()):
        if len(name) < 2:
            drop.append(name)
            continue
        # 若去掉一个垃圾尾字后仍是已存在的人名 → 并入
        for suf in GARBAGE_SUFFIX:
            if name.endswith(suf) and len(name) > len(suf):
                stem = name[: -len(suf)]
                if stem in new and stem != name:
                    log.append(f"strip {name} -> {stem}")
                    new[stem].extend(new.pop(name))
                    break
        else:
            # 整名即垃圾
            if name in {
                "周毖城", "许章白", "周官也", "王閎平", "金迁口",
                "侍中书", "为侍中",
            }:
                drop.append(name)
    for name in drop:
        if name in new:
            log.append(f"drop {name} ({len(new[name])} ev)")
            del new[name]
    return new, log


def guess_dynasty(books: list[str]) -> str:
    b = "|".join(books)
    if "三國" in b and not any(x in b for x in ("後漢", "漢書", "史記")):
        return "漢魏之際"
    if any(x in b for x in ("後漢", "后汉", "全後漢")):
        return "東漢"
    if any(x in b for x in ("漢書", "史記", "全漢文", "前漢紀")):
        return "西漢"
    return "兩漢"


def rebuild_cards(bucket: dict[str, list[dict]]) -> None:
    if not BACKUP.exists():
        shutil.copytree(CARDS, BACKUP)
    # 清掉非 backup 的 md
    for p in CARDS.glob("*.md"):
        p.unlink()
    used_ids: set[str] = set()
    # 优先给证据多的分配小 id
    ordered = sorted(bucket.items(), key=lambda x: -len(x[1]))
    for person, evs in ordered:
        books = sorted({e["book"] for e in evs})
        dyn = guess_dynasty(books)
        # id 顺序分配
        i = 1
        while f"P{i:04d}" in used_ids:
            i += 1
        pid = f"P{i:04d}"
        used_ids.add(pid)
        src_lines = []
        seen = set()
        for e in evs:
            q = (e.get("sentence") or "").replace('"', "'")[:240]
            k = q[:50]
            if k in seen:
                continue
            seen.add(k)
            src_lines.append(
                f'  - book: {e.get("book")}\n    juan: {e.get("juan")}\n    quote: 「{q}」'
            )
            if len(src_lines) >= 8:
                break
        # 试点详卡名字保留
        status = "待审" if person in {"金日磾", "金安上", "窦宪", "金建", "伍孚", "金赏", "金敞", "金涉", "金钦"} else "草稿"
        body = f"""---
id: {pid}
name: {person}
style_name: 阙
dynasty: {dyn}
status: {status}
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
{chr(10).join(src_lines) if src_lines else '  - book: 阙'}
---

## 生平履历

（待人审扩写；清洗后 evidence={len(evs)}）

## 侍中任职前后

（待校）

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
|  |  |  |  |

## 校录备注

- 规范化名：{person}
- 书目：{'/'.join(books)}
- cand: data/candidates/persons_evidence.csv（清洗后）
- 校录人/日期：待填
"""
        (CARDS / f"{person}_{dyn}.md").write_text(body, encoding="utf-8")


def write_index(bucket: dict[str, list[dict]]) -> None:
    rows = []
    for person, evs in sorted(bucket.items(), key=lambda x: -len(x[1])):
        rows.append(
            {
                "person": person,
                "n_evidence": len(evs),
                "books": "|".join(sorted({e["book"] for e in evs})),
                "sample": (evs[0].get("sentence") or "")[:120],
            }
        )
    with IDX.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["person", "n_evidence", "books", "sample"])
        w.writeheader()
        w.writerows(rows)
    with EV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["person", "cand_row", "book", "juan", "sentence", "source_file"]
        )
        w.writeheader()
        for person, evs in bucket.items():
            for e in evs:
                w.writerow({"person": person, **{k: e.get(k) for k in ("cand_row", "book", "juan", "sentence", "source_file")}})


def import_db() -> None:
    if not DB.exists():
        raise SystemExit("init_db first")
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

        pid = grab("id") or p.stem
        cur.execute(
            """INSERT OR REPLACE INTO person
            (id,name,style_name,dynasty,category,origin,birth,death,status,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                pid, grab("name"), grab("style_name"), grab("dynasty"), grab("category"),
                grab("origin"), grab("birth"), grab("death"), grab("status") or "草稿", p.name,
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


def main() -> None:
    bucket = load_evidence()
    print("before persons", len(bucket), "evidence", sum(len(v) for v in bucket.values()))
    cleaned, log = normalize_bucket(bucket)
    print("after persons", len(cleaned))
    for line in log:
        print(" ", line)
    # 校验：不得再有 金安
    if "金安" in cleaned:
        raise SystemExit("FAIL: 金安 still present")
    if "金安上" not in cleaned:
        print("WARN: 金安上 missing")
    else:
        print("OK 金安上 evidence", len(cleaned["金安上"]))
    write_index(cleaned)
    rebuild_cards(cleaned)
    print("cards", len(list(CARDS.glob('*.md'))))
    import_db()


if __name__ == "__main__":
    main()
