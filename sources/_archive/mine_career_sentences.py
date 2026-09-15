"""从原始语料按人名检索本传相关句，辅助批量补履历。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def find_person_sentences(name: str, max_files: int = 6) -> list[tuple[str, str]]:
    hits = []
    for fp in RAW.rglob("*.txt"):
        if "cards" in fp.parts:
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if name not in text:
            continue
        for sent in re.split(r"(?<=[。；])", text):
            s = sent.strip()
            if name in s and 8 <= len(s) <= 180:
                hits.append((fp.stem[:24], s[:160]))
                if len(hits) >= 20:
                    return hits
    return hits[:20]


NAMES = [
    "丁鸿", "严助", "伏完", "伏无忌", "包咸", "单飏", "陈俊", "贾复",
    "马武", "刘植", "赵憙", "蔡茂", "郑弘", "张霸", "阴识", "阴兴",
    "杨秉", "杨赐", "杨彪", "李膺", "贾彪", "张驯", "周泽", "楼望",
    "萧育", "刘淑", "刘儒", "宣秉", "爰延", "种劭", "台崇", "窦机",
    "耿承", "耿箕", "邓建", "邓干", "阎畅", "伏无忌", "许慎", "赵苞",
    "杨厚", "杨统", "刘昆", "宋登", "任安", "杨政", "李法", "施延",
    "王逸", "陈球", "何进", "梁不疑", "鲁丕", "董扶", "关兴", "宗预",
    "费祎", "董允", "陈祗", "马良", "廖立", "华歆", "钟繇", "陈群",
    "卫臻", "高堂隆", "鲍勋", "刘放", "和洽", "王蕃", "阚泽", "孙綝",
    "张布", "刘岱", "周毖", "马宇", "刘廙", "傅巽", "虞子和", "王沈",
]

if __name__ == "__main__":
    out = ROOT / "data" / "candidates" / "career_mine.txt"
    lines = []
    for n in NAMES:
        hits = find_person_sentences(n)
        if not hits:
            continue
        lines.append(f"\n======== {n} ({len(hits)}) ========")
        for juan, s in hits[:12]:
            lines.append(f"[{juan}] {s}")
    out.write_text("\n".join(lines), encoding="utf-8")
    print("names", len(NAMES), "dump", out, "bytes", out.stat().st_size)
