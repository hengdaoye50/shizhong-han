"""导出制度沿革页数据到 shizhongdata/data/institution.json。

合并：
  data/institution/institution.json  阶段 + 制度史料
  人工核对后的名录缺漏清单（写在本脚本 CURATED_GAPS）
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "institution" / "institution.json"
OUT = ROOT / "shizhongdata" / "data" / "institution.json"

# 2026-09 制度史料交叉核对后的高置信缺漏（未入 person 表）
# status: 拟补待审 | 制度人物可考 | 异写并卡 | 附录待定
CURATED_GAPS = [
    {
        "name": "辛毗",
        "dynasty_guess": "魏",
        "status": "已建卡 P0260",
        "confidence": "高",
        "evidence": "三國志多处「侍中辛毗」；与刘晔、傅巽等同列奏议",
        "sample": "於是侍中辛毗、劉曄、散騎常侍傅巽……等奏曰",
        "source": "三國志·魏书",
        "note": "2026-09 审定建卡",
    },
    {
        "name": "张辟疆",
        "dynasty_guess": "西汉",
        "status": "已建卡 P0261",
        "confidence": "高",
        "evidence": "留侯子张辟强/辟疆为侍中，年十五",
        "sample": "留侯子張辟強為侍中，年十五，謂丞相陳平曰……",
        "source": "漢書·外戚传；册府元龟/太平御览作张辟疆",
        "note": "审定用名张辟疆；异写张辟强入卡备注",
    },
    {
        "name": "孔安国",
        "dynasty_guess": "西汉",
        "status": "已建卡 P0262",
        "confidence": "高",
        "evidence": "《汉官仪》辑文：武帝时孔安国为侍中，特听掌御坐唾壶",
        "sample": "武帝時，孔安國為侍中，㠯其儒者，特聽掌御坐唾壺，朝廷榮之",
        "source": "全後漢文·卷三十四（輯《漢官儀》）；通典/初学记",
        "note": "与东晋同名孔安国切割，详见卡片备注",
    },
    {
        "name": "卓茂",
        "dynasty_guess": "更始",
        "status": "已建卡 P0263",
        "confidence": "高",
        "evidence": "更始立，以茂为侍中祭酒",
        "sample": "更始立，以茂為侍中祭酒，從至長安，知更始政亂……",
        "source": "後漢書·卓茂传",
        "note": "2026-09 审定建卡",
    },
    {
        "name": "卫觊",
        "dynasty_guess": "汉魏之际",
        "status": "已建卡 P0264",
        "confidence": "高",
        "evidence": "魏国既建，拜侍中，与王粲并典制度",
        "sample": "魏國旣建，拜侍中，與王粲並典制度",
        "source": "三國志·魏书·王卫二刘傅传",
        "note": "2026-09 审定建卡",
    },
    {
        "name": "孙资",
        "dynasty_guess": "魏",
        "status": "已建卡 P0265",
        "confidence": "高",
        "evidence": "曹爽诛后，复以资为侍中，领中书令",
        "sample": "曹爽誅後，復以資為侍中，領中書令",
        "source": "三國志·魏书",
        "note": "与刘放（P0030）成对",
    },
    {
        "name": "丁冲",
        "dynasty_guess": "汉魏之际",
        "status": "已建卡 P0266",
        "confidence": "中高",
        "evidence": "侍中丁冲与伏完、种辑同封",
        "sample": "封衞將軍董承、輔國將軍伏完、侍中丁沖、种輯……為列侯",
        "source": "後漢書卷72注引袁宏纪；册府元龟",
        "note": "来源已复核；字里仍阙",
    },
    {
        "name": "李祯",
        "dynasty_guess": "汉魏之际",
        "status": "已建卡 P0268",
        "confidence": "中",
        "evidence": "侍中李祯，李傕州里，语傕以国家故事",
        "sample": "侍中李禎，傕州里，素與傕通，語傕「所以持刀者，軍中不可不爾，此國家故事」",
        "source": "三國志·卷06 董二袁刘传",
        "note": "2026-09 审定建卡",
    },
    {
        "name": "梁安国",
        "dynasty_guess": "东汉",
        "status": "已建卡 P0269",
        "confidence": "中",
        "evidence": "梁棠卒，子安国嗣，延光中为侍中，有罪免官",
        "sample": "棠卒，子安國嗣，延光中為侍中，有罪免官",
        "source": "後漢書·梁统列传卷34",
        "note": "外戚网络补点",
    },
    {
        "name": "张涉",
        "dynasty_guess": "西汉",
        "status": "误抽不建",
        "confidence": "—",
        "evidence": "敞子涉本为左曹，上拜涉为侍中",
        "sample": "敞子涉本為左曹，上拜涉為侍中，使待幸綠車載送衛尉舍",
        "source": "漢書·金日磾传（霍光金日磾传系）",
        "note": "实为金敞子金涉，库内已有 P0222；非张安世族",
    },
    {
        "name": "金建",
        "dynasty_guess": "西汉",
        "status": "已建卡 P0267",
        "confidence": "中高",
        "evidence": "金日磾两子赏、建，俱侍中",
        "sample": "日磾兩子，賞、建，俱侍中，與昭帝略同年",
        "source": "漢書·金日磾传",
        "note": "与金赏 P0224 对称建卡",
    },
    {
        "name": "周珌",
        "dynasty_guess": "东汉",
        "status": "异写并卡",
        "confidence": "中",
        "evidence": "时侍中周珌、城门校尉伍琼为卓所信待",
        "sample": "時侍中周珌、城門校尉伍瓊為卓所信待",
        "source": "後漢書·董卓传系卷74上",
        "note": "并入周毖 P0056，异写句已补 source",
    },
]

CURATED_NOTES = [
    "自动抽取句中大量「年十八」「再迁」「宣意」等为噪声，已剔除，见 data/candidates/roster_gap_noise.csv。",
    "杜乔、王辅、周广、伍琼、窦宪、霍去病、刘晔、董允、张纯、王望、王闳、桑弘羊、来历、史丹等传统字形条目均已在库。",
    "制度条（皆加官、无员、少府属官等）不建人卡，已编入制度沿革各阶段。",
    "2026-09 人工审定：10 人建卡入正式库；张涉误抽（=金涉）；周珌异写并入周毖。",
]


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    data["roster_check"] = {
        "roster_size": 268,
        "audit_date": "2026-09",
        "method": "data/raw 全语料含「侍中」句抽取 + person 表对照 + 人工复核 + 审定建卡",
        "corpus_sentences": data.get("stats", {}).get("corpus_sentences_scanned") or 1501,
        "gaps": CURATED_GAPS,
        "notes": CURATED_NOTES,
        "files": [
            "docs/roster_gap_report.md",
            "data/candidates/roster_gap_v2.csv",
            "data/candidates/roster_gap_noise.csv",
            "data/candidates/institution_review.csv",
        ],
    }
    data["nav_title"] = "制度沿革"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT, "phases", len(data["phases"]), "gaps", len(CURATED_GAPS))


if __name__ == "__main__":
    main()
