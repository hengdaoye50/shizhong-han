"""全语料再扫：凡「侍中」句，无可靠人名者输出待考/佚名条目。

输出 data/candidates/anonymous_shizhong.csv
列: book, juan, sentence, source_file, anon_label, note
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "candidates" / "anonymous_shizhong.csv"

SURNAMES = (
    "霍|金|上官|桑|杨|楊|张|張|王|李|赵|趙|陈|陳|刘|劉|邓|鄧|耿|窦|竇|马|馬|班|梁|袁|曹|"
    "孙|孫|周|吴|吳|郑|鄭|朱|许|許|冯|馮|董|萧|蕭|程|傅|贾|賈|夏侯|诸葛|諸葛|司马|司馬|"
    "皇甫|鲁|魯|尹|何|郭|阴|陰|来|來|岑|任|宋|杜|桓|虞|黄|黃|蔡|荀|孔|钟|鍾|华|華|卫|衛|"
    "陆|陸|顾|顧|纪|紀|徐|谢|謝|韩|韓|唐|石|白|侯|段|汪|田|姚|毛|秦|江|史|黎|乔|喬|龚|龔|"
    "于|於|齐|齊|康|伍|余|元|刁|单|單|施|丁|贺|郗|习|習|滕|是|步|灌|祭|铫|銚|濮|淳于|申屠|"
    "毋|兒|儿|奚|嵇|阮|向|伏|承|爰|种|臺|台|宗|关|關|廖|赵|趙|鲁|鲁|钟|鍾"
)

NAME = rf"(?:{SURNAMES})[一-龥]{{1,2}}"

# 已在卡的人名（粗）
KNOWN = set()
for p in (ROOT / "data" / "cards").glob("*.md"):
    KNOWN.add(p.stem.split("_")[0])

# 佚名/待考模式
ANON_PATTERNS = [
    # 侍中某（无姓）
    (re.compile(r"侍中([一-龥]{1,2})(?=君|等|曰|言|上|下|入|出|为|為|拜|迁|遷|以|与|與|及|因|遂|乃|辄|數|数)"), "侍中+名"),
    # 皇帝问侍中君卿等（有字无姓）
    (re.compile(r"問侍中([一-龥]{2})"), "问侍中X"),
    # 百官表 | xxx为侍中 |
    (re.compile(r"[|｜][^|｜]{0,12}為侍中"), "百官表"),
]


def is_known_name(s: str) -> bool:
    for n in KNOWN:
        if n and n in s:
            return True
    if re.search(rf"{NAME}", s):
        return True
    return False


def main() -> None:
    rows = []
    files = list(RAW.rglob("*.txt"))
    # 只处理 wiki/mirror 正文，排除我们自己写的 cards
    files = [f for f in files if "cards" not in f.parts]
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "侍中" not in text:
            continue
        rel = str(fp.relative_to(ROOT)).replace("\\", "/")
        for sent in re.split(r"(?<=[。！？；])", text):
            if "侍中" not in sent:
                continue
            sent = sent.strip()
            if len(sent) < 6:
                continue
            # 句中若已有明确姓+名且在 KNOWN，跳过
            names_in = re.findall(NAME, sent)
            if any(n in KNOWN for n in names_in):
                continue
            # 有姓+名但不在 KNOWN：可能是新人，保留但标「有名待核」
            has_surname_name = bool(re.search(rf"{NAME}", sent))
            # 无名侍中
            if re.search(r"侍中[一-龥]{0,2}(君|等|曰|言|上书|上疏|入|出|为|為|拜|迁|遷|持节|持節)", sent) or \
               re.search(r"(拜|迁|遷|徵|征|擢|复|復|再|入|出|加)[一-龥]{0,4}侍中$", sent) or \
               "百官" in rel or "表" in fp.name:
                label = "佚名/待考"
                if has_surname_name:
                    label = "有名待核"
                # 特殊
                if "君卿" in sent:
                    label = "侍中君卿（佚姓）"
                if "子侯" in sent:
                    label = "侍中子侯"
                rows.append(
                    {
                        "book": fp.parent.name if fp.parent.name not in ("raw",) else rel.split("/")[1],
                        "juan": fp.stem[:40],
                        "sentence": sent[:300],
                        "source_file": rel,
                        "anon_label": label,
                        "note": "",
                    }
                )
    print("anon rows", len(rows))
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["book", "juan", "sentence", "source_file", "anon_label", "note"])
        w.writeheader()
        w.writerows(rows)
    print("->", OUT)


if __name__ == "__main__":
    main()
