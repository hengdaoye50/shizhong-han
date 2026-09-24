# -*- coding: utf-8 -*-
"""enrich 拒项批量改判：高置信明文收源入卡。"""
from pathlib import Path
import re

ROOT = Path(r"D:\CODEX\两汉侍中数据库搭建")
CARDS = ROOT / "data" / "cards"

# (文件名片段, quote, book, juan)  —— 每人每书卷一条，去重后写入
ACCEPTS = {
    "傅嘉": [
        ("「復免傅嘉，曰：『前為侍中，毀譖仁賢，誣訴大臣』」", "漢書", "卷81"),
    ],
    "史丹": [
        ("「賴侍中史丹護太子家，輔助有力」", "漢書", "卷10"),
        ("「刺侍中史丹擁右太子，語在《丹傳》」", "漢書", "卷98"),
        ("「樂陵侯史丹者……爲侍中，護太子家」", "前漢紀", "卷23"),
    ],
    "史恃": [
        ("「詔使侍中史恃、太僕韓融告張濟」", "後漢紀", "卷28"),
    ],
    "和逌": [
        ("「侍中和逌、尚書陳騫等作詩稽留」", "三國志", "卷4"),
    ],
    "徐博": [
        ("「侍中徐博賦四篇」", "漢書", "卷30"),
    ],
    "李充": [
        ("「徵充爲博士，俄遷侍中」", "後漢紀", "卷15"),
    ],
    "淳于恭": [
        ("「侍中淳于恭奏，帝親稱制臨決」", "後漢書", "卷3"),
        ("「使五官中郎將魏應主承制問難，侍中淳于恭奏上」", "後漢書", "卷37"),
    ],
    "王接": [
        ("「侍中衞尉王接為大司馬車騎將軍」", "漢書", "卷19"),
        ("「侍中衛尉王接爲大司馬車騎將軍」", "前漢紀", "卷22"),
    ],
    "王方": [
        ("「方致位侍中」", "後漢書", "卷25"),
        ("「徵爲博士、侍中」", "後漢紀", "卷14"),
    ],
    "王林卿": [
        ("「侍中王林卿通輕俠，傾京師」", "漢書", "卷77"),
        ("「何並斬侍中王林卿奴，是立志也」", "漢書", "卷100下"),
    ],
    "王能": [
        ("「衞尉王能為侍中光祿勳」", "漢書", "卷19"),
    ],
    "王莽": [
        ("「封舅曼子侍中騎都尉光祿大夫王莽爲新都侯」", "漢書", "卷10"),
        ("「侍中騎都尉光祿大夫王莽為大司馬」", "漢書", "卷19"),
    ],
    "王音": [
        ("「侍中中郎將王音為太僕」", "漢書", "卷19"),
        ("「時鳳弟侍中王音私聽之，告鳳」", "前漢紀", "卷25"),
    ],
    "荀勖": [
        ("「侍中領中書監濟北侯臣荀勖」", "三國志", "卷35"),
    ],
    "蔡邕": [
        ("「遷巴郡太守，復留為侍中」", "後漢書", "卷60下"),
        ("「卓怒，罷坐，欲誅植，侍中蔡邕勸之，得免」", "三國志", "卷6"),
    ],
    "郭攸之": [
        ("「侍中、侍郎郭攸之、費禕、董允等」", "三國志", "卷35"),
        ("「侍中郭攸之、費禕、侍郎董允」", "三國志", "卷39"),
    ],
    "金敞": [
        ("「侍中奉車都尉金敞為水衡都尉」", "漢書", "卷19"),
        ("「與侍中金敞並拾遺左右」", "漢書", "卷78"),
        ("「時蕭望之、周堪、劉向及侍中金敞」", "前漢紀", "卷21"),
    ],
    "郤巡": [
        ("「陳郡郤巡，學傳英業，官至侍中」", "後漢書", "卷82上"),
    ],
}


def find_card(name: str):
    for p in CARDS.glob("*.md"):
        t = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^name:\s*(.+)$", t, re.M)
        if m and m.group(1).strip() == name:
            return p
    return None


def patch(name: str, entries):
    p = find_card(name)
    if not p:
        print("MISSING CARD", name)
        return
    t = p.read_text(encoding="utf-8")
    added = 0
    for quote, book, juan in entries:
        if quote[:12] in t:
            continue
        # 插入 sources 块：quote/book/juan
        block = f"  - quote: {quote}\n    book: {book}\n    juan: {juan}\n"
        if "sources:\n" in t:
            t = t.replace("sources:\n", "sources:\n" + block, 1)
        else:
            t = t.replace("shizhong_terms:", f"sources:\n{block}shizhong_terms:", 1)
        added += 1
    if added:
        note = f"enrich 拒项改判收源 {added} 条（2026-09 人工审定）"
        if note not in t:
            if "## 校录备注" in t:
                t = t.replace("## 校录备注\n", f"## 校录备注\n\n- {note}\n", 1)
            else:
                t = t.rstrip() + f"\n\n## 校录备注\n\n- {note}\n"
        # 若 nature 仍非「有明文」，补 evidence
        if "evidence: 有明文" not in t:
            t = re.sub(r"(    evidence: ).*", r"\1有明文", t, count=1)
        p.write_text(t, encoding="utf-8")
        print(f"PATCHED {name} +{added} sources")
    else:
        print(f"NOCHANGE {name}")


def main():
    for name, entries in ACCEPTS.items():
        patch(name, entries)
    print("DONE", len(ACCEPTS), "persons")


if __name__ == "__main__":
    main()
