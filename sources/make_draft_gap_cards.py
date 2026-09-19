"""为高置信拟补人物生成「审定用草稿卡」（不入正式库）。

输出目录: data/candidates/draft_cards/
正式建卡时请复制到 data/cards/ 并人工校定后跑 cleanup 入库。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "candidates" / "draft_cards"

# name, dynasty, category, origin, quotes[(book,juan,quote)], notes
DRAFTS = [
    {
        "name": "辛毗",
        "dynasty": "魏",
        "category": "士人",
        "origin": "颍川阳翟",
        "quotes": [
            ("三國志", "魏书相关", "於是侍中辛毗、劉曄、散騎常侍傅巽、衞臻、尚書令桓階、尚書陳矯、陳羣……等奏曰"),
            ("三國志", "魏书相关", "侍中辛毗等谏猎/议政类记载（建卡时补全卷次）"),
        ],
        "notes": "拟补队列高置信；建议核三國志本传与侍中拜罢时间。",
        "nature": "正职/近臣顾问",
        "evidence": "有明文",
    },
    {
        "name": "张辟强",
        "dynasty": "西汉",
        "category": "勋贵",
        "origin": "留侯张良子",
        "quotes": [
            ("漢書", "外戚传上", "留侯子張辟強為侍中，年十五，謂丞相陳平曰：「太后獨有帝，今哭而不悲，君知其解未？」"),
        ],
        "notes": "西汉早期侍中个案；吕后崩后政治节点，可与陈平、周勃关系网对读。",
        "nature": "加官/近侍",
        "evidence": "有明文",
    },
    {
        "name": "孔安国",
        "dynasty": "西汉",
        "category": "士人",
        "origin": "鲁",
        "quotes": [
            ("全後漢文（辑漢官儀）", "卷三十四", "武帝時，孔安國為侍中，㠯其儒者，特聽掌御坐唾壺，朝廷榮之"),
        ],
        "notes": "制度史关键：儒者侍中与近臣职掌。出处为辑本《汉官仪》，建卡时注明辑佚性质。",
        "nature": "儒者近臣；掌御坐唾壶",
        "evidence": "有明文（辑本）",
    },
    {
        "name": "卓茂",
        "dynasty": "更始",
        "category": "士人",
        "origin": "南阳宛",
        "quotes": [
            ("後漢書", "卓茂传", "更始立，以茂為侍中祭酒，從至長安，知更始政亂，以年老乞骸骨歸"),
        ],
        "notes": "更始政权侍中祭酒；后为东汉名臣，制度衔接样本。",
        "nature": "侍中祭酒（复合官）",
        "evidence": "有明文",
    },
    {
        "name": "卫觊",
        "dynasty": "汉魏之际",
        "category": "士人",
        "origin": "河东安邑",
        "quotes": [
            ("三國志", "王卫二刘傅传", "魏國旣建，拜侍中，與王粲並典制度"),
        ],
        "notes": "与王粲（已有卡）并典制度，汉魏侍中制度化的直接证据。",
        "nature": "侍中；典制度",
        "evidence": "有明文",
    },
    {
        "name": "孙资",
        "dynasty": "魏",
        "category": "士人",
        "origin": "太原",
        "quotes": [
            ("三國志", "魏书", "曹爽誅後，復以資為侍中，領中書令"),
        ],
        "notes": "与刘放（P0030）并称；建议成对建卡并补关系边。",
        "nature": "侍中领中书令",
        "evidence": "有明文",
    },
    {
        "name": "丁冲",
        "dynasty": "汉魏之际",
        "category": "待考",
        "origin": "阙",
        "quotes": [
            ("後漢書", "献帝相关", "封衞將軍董承、輔國將軍伏完、侍中丁沖、种輯……為列侯"),
        ],
        "notes": "献帝朝侍中；与伏完、种辑、刘艾对照。籍贯字里建卡时再核。",
        "nature": "侍中",
        "evidence": "有明文",
    },
    {
        "name": "金建",
        "dynasty": "西汉",
        "category": "降人",
        "origin": "匈奴休屠→汉",
        "quotes": [
            ("漢書", "金日磾传", "日磾兩子，賞、建，俱侍中，與昭帝略同年，共卧起"),
        ],
        "notes": "金日磾子；金赏已有卡（P0224）。建可独立建卡或并注于金氏世系。",
        "nature": "侍中（与赏俱）",
        "evidence": "有明文",
    },
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for i, d in enumerate(DRAFTS, 1):
        pid = f"DRAFT{i:02d}"
        q_lines = "\n".join(
            f"  - book: {b}\n    juan: {j}\n    quote: 「{q}」" for b, j, q in d["quotes"]
        )
        body = f"""---
# 审定草稿 — 未入正式库 / data/cards/
id: {pid}
name: {d['name']}
style_name:
dynasty: {d['dynasty']}
status: 待审
category: {d['category']}
origin: {d['origin']}
birth: 阙
death: 阙
shizhong_terms:
  - start: 阙
    end: 阙
    nature: {d['nature']}
    evidence: {d['evidence']}
sources:
{q_lines}
---

## 生平履历

1. （待补）据下列原典整理任职前后事迹。

## 侍中任职前后

- {d['nature']}

## 关系

| 对象 | 关系类型 | 说明 | 出处 |
|------|----------|------|------|
| （待补） |  |  |  |

## 校录备注

- {d['notes']}
- 来源：制度沿革名录核对（docs/roster_gap_report.md）
- 处理：人工确认后复制到 data/cards/<姓名>_<朝代>.md，再跑入库流水线
"""
        path = OUT / f"{d['name']}_{d['dynasty']}_草稿.md"
        path.write_text(body, encoding="utf-8")
        print("draft", path.name)
    print(f"wrote {len(DRAFTS)} drafts -> {OUT}")


if __name__ == "__main__":
    main()
