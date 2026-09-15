"""规范 rel_type、补全世系对称边，重建 relation 表。"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"
DB = ROOT / "data" / "db" / "shizhong.db"
OUT = ROOT / "data" / "db" / "relations_full.csv"

# 映射到规范类型
NORM = {
    "与帝": "与帝",
    "与帝系": "与帝",
    "与帝/权臣": "与帝",
    "与帝/姻亲": "与帝",
    "权臣": "与大将军",
    "与大将军": "与大将军",
    "与宦官": "与宦官",
    "举主": "举主",
    "荐主": "举主",
    "府主": "府主",
    "府主/同僚": "府主",
    "师": "师",
    "同门": "同门",
    "同僚": "同僚",
    "同列": "同僚",
    "同僚/说客": "同僚",
    "同僚/被诘": "同僚",
    "同僚/献计对象": "同僚",
    "政敌": "政敌",
    "政敌系": "政敌",
    "同谋": "同谋",
    "同党": "同谋",
    "前后任": "前后任",
    "父": "父",
    "母": "母",
    "子": "子",
    "女": "女",
    "兄": "兄弟",
    "弟": "兄弟",
    "兄弟": "兄弟",
    "兄/兄弟": "兄弟",
    "从兄": "从父",
    "从弟": "从父",
    "从父": "从父",
    "从子": "从子",
    "从祖": "先祖",
    "从兄弟": "从父",
    "祖": "祖",
    "曾祖": "曾祖",
    "高祖": "高祖",
    "先祖": "先祖",
    "宗族": "宗族",
    "外戚": "外戚",
    "妻": "夫妻",
    "夫": "夫妻",
    "夫妻": "夫妻",
    "姻亲": "姻亲",
    "尚主": "姻亲",
    "姊妹": "兄弟",
    "姊": "兄弟",
    "妹": "兄弟",
    "舅": "姻亲",
    "甥": "姻亲",
    "外甥": "姻亲",
    "岳父": "姻亲",
    "养父系": "宗族",
    "旧主": "府主",
    "前朝": "与帝",
    "部属": "同僚",
    "同僚": "同僚",
    "交游": "同僚",
    "形势": "同僚",
    "暗通": "同谋",
    "知人": "举主",
    "问者（晋）": "同僚",
    "问者对象": "同僚",
    "被问": "同僚",
    "请主": "举主",
    "所迎": "同僚",
    "誉莽": "同僚",
    "制度触发": "其他",
    "父/兄弟": "父",
}

# 世系对称
INVERSE = {
    "父": "子",
    "母": "子",
    "子": "父",
    "女": "父",
    "祖": "孙（待核）",
    "兄弟": "兄弟",
    "从父": "从子",
    "从子": "从父",
    "曾祖": "从孙（待核）",
    "妻": "夫妻",
    "夫妻": "夫妻",
}


def parse_front(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm = m.group(1)

    def grab(k: str) -> str:
        mm = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
        return mm.group(1).strip() if mm else ""

    return {"id": grab("id"), "name": grab("name")}


def parse_rel_table(text: str) -> list[tuple[str, str, str, str]]:
    rows = []
    if "## 关系" not in text:
        return rows
    part = text.split("## 关系", 1)[1]
    if "\n## " in part:
        part = part.split("\n## ", 1)[0]
    for line in part.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or not cells[0] or cells[0] == "对象":
            continue
        if set(cells[0]) <= {"-", " "}:
            continue
        rows.append((cells[0], cells[1] if len(cells) > 1 else "", cells[2] if len(cells) > 2 else "", cells[3] if len(cells) > 3 else ""))
    return rows


def main() -> None:
    person_by_name = {}
    raw = []
    for p in sorted(CARDS.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        meta = parse_front(text)
        name = meta.get("name") or p.stem.split("_")[0]
        pid = meta.get("id") or ""
        person_by_name[name] = pid
        for obj, rtype, note, src in parse_rel_table(text):
            raw.append({"from_id": pid, "from_name": name, "to_name": obj, "rel_type": rtype, "note": note, "source": src})

    # 规范化
    out = []
    for r in raw:
        t = NORM.get(r["rel_type"].strip(), "其他")
        if r["rel_type"] not in NORM and r["rel_type"]:
            # 复合：取第一个词
            t0 = r["rel_type"].split("/")[0].split("（")[0].strip()
            t = NORM.get(t0, "其他")
        rr = dict(r)
        rr["rel_type"] = t
        rr["to_id"] = person_by_name.get(r["to_name"], "")
        rr["status"] = "草稿"
        out.append(rr)

    # 世系对称（仅 to_id 非空且非自我）
    extra = []
    for r in out:
        inv = INVERSE.get(r["rel_type"])
        if not inv or not r["to_id"] or r["to_id"] == r["from_id"]:
            continue
        # 找 to 的 name
        to_name = r["to_name"]
        extra.append({
            "from_id": r["to_id"],
            "from_name": to_name,
            "to_id": r["from_id"],
            "to_name": r["from_name"],
            "rel_type": inv,
            "note": f"对称边←{r['from_name']}-{r['rel_type']}",
            "source": r.get("source", ""),
            "status": "草稿",
        })
    out.extend(extra)

    # 去重
    seen = set()
    uniq = []
    for r in out:
        key = (r["from_name"], r["to_name"], r["rel_type"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["from_id", "from_name", "to_id", "to_name", "rel_type", "note", "source", "status"])
        w.writeheader()
        w.writerows(uniq)

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DELETE FROM relation")
    for r in uniq:
        cur.execute(
            "INSERT INTO relation (from_id,from_name,to_id,to_name,rel_type,note,status) VALUES (?,?,?,?,?,?,?)",
            (r["from_id"], r["from_name"], r["to_id"], r["to_name"], r["rel_type"], (r.get("note") or "")[:200], r["status"]),
        )
    con.commit()
    cur.execute("SELECT rel_type, COUNT(*) c FROM relation GROUP BY rel_type ORDER BY c DESC")
    print("total", len(uniq))
    for t, c in cur.fetchall():
        print(f"  {c:4d}  {t}")
    cur.execute("SELECT COUNT(*) FROM relation WHERE to_id!=''")
    print("both linked", cur.fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
