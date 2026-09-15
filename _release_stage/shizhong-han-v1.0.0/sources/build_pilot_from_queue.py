import csv
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "data/candidates/pilot_queue.csv").read_bytes().decode("gb18030")
rows = list(csv.DictReader(text.splitlines()))
fields = list(rows[0].keys())
out = ROOT / "data/candidates/pilot_queue.csv"
with out.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
print("re-saved utf-8-sig", len(rows))

by = defaultdict(list)
for r in rows:
    if (r.get("status") or "").strip() != "已录":
        continue
    persons = [p.strip() for p in (r.get("person") or "").replace("、", ",").split(",") if p.strip()]
    for p in persons:
        by[p].append(r)

meta = {
    "金日磾": ("P0001", "西漢", "降人", "翁叔"),
    "金安上": ("P0002", "西漢", "降人", "子侯"),
    "金赏": ("P0003", "西漢", "降人", ""),
    "金建": ("P0004", "西漢", "降人", ""),
    "金敞": ("P0005", "西漢", "降人", ""),
    "金涉": ("P0006", "西漢", "降人", ""),
    "金钦": ("P0007", "西漢", "降人", ""),
    "窦宪": ("P0010", "東漢", "外戚", "伯度"),
    "梁不疑": ("P0011", "東漢", "外戚", ""),
    "鲁丕": ("P0012", "東漢", "士人", ""),
    "刘瑜": ("P0013", "東漢", "士人", ""),
    "尹勋": ("P0014", "東漢", "士人", ""),
    "莽何罗": ("P0015", "西漢", "其他", ""),
    "史高": ("P0016", "西漢", "外戚", ""),
    "董扶": ("P0017", "東漢", "士人", ""),
    "郭举": ("P0018", "東漢", "外戚", ""),
    "耿良": ("P0019", "東漢", "外戚", ""),
    "贾逵": ("P0020", "東漢", "士人", ""),
}

cards = ROOT / "data/cards"
cards.mkdir(exist_ok=True)


def esc(s: str) -> str:
    return (s or "").replace('"', "'")


for name, evidence in sorted(by.items(), key=lambda x: -len(x[1])):
    pid, dyn, cat, style = meta.get(name, ("P9xxx", "兩漢", "其他", ""))
    fn = cards / f"{name}_{dyn}.md"
    srcs = []
    seen = set()
    for r in evidence:
        q = esc((r.get("sentence") or "").strip())
        key = (r.get("book"), r.get("juan"), q[:40])
        if key in seen:
            continue
        seen.add(key)
        srcs.append(f'  - book: {r.get("book")}\n    juan: {r.get("juan")}\n    quote: 「{q}」')
    notes = []
    for r in evidence:
        n = (r.get("review_note") or "").strip()
        if n:
            notes.append(f"- {n}")
    src_block = "\n".join(srcs) if srcs else "  - book: 阙"
    note_block = "\n".join(notes) if notes else "- （无审录备注）"
    body = f"""---
id: {pid}
name: {name}
style_name: {style}
dynasty: {dyn}
status: 已校
category: {cat}
origin: 阙
birth: 阙
death: 阙
shizhong_terms:
  - start: 阙
    end: 阙
    nature: 阙
    evidence: 有明文
sources:
{src_block}
---

## 生平履历

（待据已录句与本传扩写）

## 侍中任职前后

（待校）

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
|  |  |  |  |

## 校录备注

- 由 pilot_queue 已录句自动生成骨架，条数：{len(evidence)}
{note_block}
- cand: data/candidates/pilot_queue.csv
- 校录人/日期：—
"""
    fn.write_text(body, encoding="utf-8")
    print("card", fn.name, "evidence", len(evidence))

rel = ROOT / "data/db/pilot_relations.csv"
rel_rows = [
    ["P0001", "金日磾", "P0003", "金赏", "父", "日磾子，后为侍中太仆", "已录源"],
    ["P0001", "金日磾", "P0004", "金建", "父", "日磾子，俱侍中", "已录源"],
    ["P0001", "金日磾", "P0002", "金安上", "从父", "伦支", "已录源"],
    ["P0002", "金安上", "P0005", "金敞", "父", "安上子，中郎将侍中", "已录源"],
    ["P0001", "金日磾", "", "霍光", "同僚", "共诛莽何罗；妻以女", "草稿"],
    ["P0001", "金日磾", "", "莽何罗", "政敌", "侍中仆射谋反，日磾讨之", "已录源"],
    ["P0002", "金安上", "", "霍禹", "政敌", "霍氏反拒亲属", "草稿"],
    ["P0002", "金安上", "", "史高", "同僚", "共发霍氏", "已录源"],
    ["P0002", "金安上", "", "宣帝", "与帝", "少为侍中见爱", "草稿"],
    ["P0002", "金安上", "", "萧望之", "同僚", "使谕意/诘问", "已录源"],
    ["P0005", "金敞", "", "萧望之", "同僚", "与刘向拾遗左右", "已录源"],
    ["P0010", "窦宪", "", "章德窦皇后", "外戚", "皇后弟", "草稿"],
    ["P0010", "窦宪", "", "和帝", "与帝", "外戚之重", "草稿"],
    ["P0010", "窦宪", "", "张林", "举主", "荐为尚书", "已录源"],
    ["P0010", "窦宪", "", "陈宠", "政敌", "宠斥林", "已录源"],
    ["P0010", "窦宪", "", "崔骃", "府主", "文章往来", "已录源"],
    ["P0010", "窦宪", "", "郭举", "姻亲", "女弟婿为侍中", "已录源"],
    ["P0011", "梁不疑", "", "梁冀", "兄弟", "冀弟侍中", "已录源"],
    ["P0013", "刘瑜", "", "窦武", "举主", "武引为侍中", "已录源"],
    ["P0013", "刘瑜", "P0014", "尹勋", "同僚", "共谋诛宦官", "已录源"],
    ["P0014", "尹勋", "", "窦武", "同僚", "武引为尚书令", "已录源"],
    ["P0017", "董扶", "", "何进", "举主", "进荐拜侍中", "已录源"],
    ["P0012", "鲁丕", "", "邓骘", "举主", "大将军举丕再为侍中", "已录源"],
    ["P0019", "耿良", "", "安帝妹", "姻亲", "侍中尚濮阳长公主", "已录源"],
]
with rel.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["from_id", "from_name", "to_id", "to_name", "rel_type", "note", "status"])
    w.writerows(rel_rows)
print("relations", len(rel_rows), "->", rel)
print("done persons", len(by))
