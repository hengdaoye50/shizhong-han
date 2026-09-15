"""批量扫描剩余列传：输出 侍中句 + 前文最近「X字」，供定人建卡。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIRROR = ROOT / "data" / "raw" / "mirror"
OUT = ROOT / "data" / "candidates" / "todo_bios_ctx.txt"

# 优先高价值文件名子串
PRIORITY = [
    # 漢書
    "王莽传", "元后传", "外戚传", "萧望之传", "盖诸葛刘郑", "何武王嘉师丹",
    "匡张孔马", "翟方进", "严朱吾丘", "公孙刘田", "楚元王", "谷永杜邺",
    "百官公卿表",
    # 後漢書
    "杨震列传", "邓寇", "窦融", "卓鲁魏刘", "宣张二王杜郭", "桓荣丁鸿",
    "樊宏阴识", "梁统", "李杜", "窦何", "郑孔荀", "董卓", "袁绍刘表",
    "皇甫张段", "张王种陈", "崔骃", "伏侯宋蔡", "杨李翟应", "朱冯虞郑",
    "刘赵淳于", "苏竟杨厚", "耿弇", "冯岑贾", "吴盖陈臧", "宗室四王",
    "申屠刚", "桓谭冯衍",
]


def scan_file(fp: Path, out_lines: list[str]) -> int:
    try:
        text = fp.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0
    if "侍中" not in text:
        return 0
    n = 0
    for sent in re.split(r"(?<=[。！？；])", text):
        if "侍中" not in sent:
            continue
        sent = sent.strip()
        if len(sent) < 8:
            continue
        idx = text.find(sent[:24])
        ctx = text[max(0, idx - 280) : idx].replace("\n", " ") if idx >= 0 else ""
        m = list(re.finditer(r"([一-龥]{2,3})字[一-龥]{1,3}", ctx))
        owner = m[-1].group(1) if m else "?"
        out_lines.append(f"{fp.parent.name}|{fp.name}|{owner}|{sent[:200]}")
        n += 1
    return n


def main() -> None:
    lines: list[str] = []
    total = 0
    seen = set()
    # 优先
    for key in PRIORITY:
        for fp in MIRROR.rglob(f"*{key}*原文*.txt"):
            if fp in seen:
                continue
            seen.add(fp)
            total += scan_file(fp, lines)
        for fp in MIRROR.rglob(f"*{key}.txt"):
            if fp in seen:
                continue
            seen.add(fp)
            total += scan_file(fp, lines)
    # 其余 TODO 含侍中的（排除已 DONE 类传）
    skip = ["儒林", "党锢", "文苑", "独行", "方术", "循吏", "酷吏", "宦者", "皇后", "张曹郑", "霍光金日", "张汤", "王商史丹", "佞幸"]
    for fp in MIRROR.rglob("*.txt"):
        if fp in seen:
            continue
        if any(s in fp.name for s in skip):
            continue
        total += scan_file(fp, lines)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("lines", len(lines), "hits", total, "->", OUT)


if __name__ == "__main__":
    main()
