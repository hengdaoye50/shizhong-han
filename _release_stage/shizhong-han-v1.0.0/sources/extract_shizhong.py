"""从 data/raw 文本中抽取含「侍中」的候选句，输出 CSV 供人工校录。

用法:
  python sources/extract_shizhong.py --input data/raw --output data/candidates/shizhong_candidates.csv
  python sources/extract_shizhong.py --input data/raw/漢書 --output data/candidates/hanshu.csv
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 与侍中直接相关、或易混淆的复合官名，抽取时原样保留 match_type 提示
COMPOUND = re.compile(
    r"(侍中僕射|侍中中臣|諸曹侍中|侍中史|侍中尚書|給事中侍中|侍中領|侍中兼)"
)

# 句边界：中西文句读 + 换行
SENT_SPLIT = re.compile(r"(?<=[。！？；\n])")

# 人名启发式：前 1–3 字常见姓 + 名，仅作提示，不作定论
SURNAME = (
    "霍|金|上官|桑|杨|楊|张|張|王|李|赵|趙|陈|陳|刘|劉|邓|鄧|耿|窦|竇|马|馬|"
    "班|梁|袁|曹|孙|孫|周|吴|吴|鄭|郑|朱|许|許|冯|馮|于|於|董|萧|蕭|程|傅|"
    "贾|賈|夏侯|诸葛|諸葛|司马|司馬|皇甫|宇文|慕容"
)


def iter_txt_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(root.rglob("*.txt"))


def book_from_path(path: Path, base: Path) -> str:
    try:
        rel = path.relative_to(base)
    except ValueError:
        return path.parent.name
    parts = list(rel.parts)
    if parts and parts[0] == "mirror" and len(parts) > 1:
        return parts[1]
    return parts[0] if len(parts) > 1 else path.parent.name


def juan_from_stem(stem: str) -> str:
    m = re.search(r"卷\s*([0-9０-９]+[上下]*)", stem)
    if m:
        return m.group(1)
    m2 = re.match(r"(第[一二三四五六七八九十百零〇\d]+章)-(.+)", stem)
    if m2:
        return f"{m2.group(1)}:{m2.group(2)}"
    return stem


def near_name(sentence: str, window: int = 12) -> str:
    """在「侍中」前 window 字内找疑似人名，找不到返回空。"""
    idx = sentence.find("侍中")
    if idx < 0:
        return ""
    left = sentence[max(0, idx - window) : idx]
    # 优先：X（字Y）/ 人名+動詞+侍中 的近邻
    m = re.search(rf"({SURNAME})[一-龥]{{0,2}}$", left)
    if m:
        # 再贪一点：把姓后可能的名吞进来
        m2 = re.search(rf"({SURNAME}[一-龥]{{1,2}})$", left)
        return m2.group(1) if m2 else m.group(1)
    # 「侍中某」形式（侍中后直接人名）
    after = sentence[idx + 2 : idx + 6]
    m3 = re.match(rf"({SURNAME}[一-龥]{{1,2}})", after)
    if m3:
        return m3.group(1)
    return ""


def extract_file(path: Path, base: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    rows: list[dict] = []
    for sent in SENT_SPLIT.split(text):
        sent = sent.strip()
        if "侍中" not in sent:
            continue
        # 过长段落截取侍中附近
        if len(sent) > 400:
            i = sent.find("侍中")
            sent = sent[max(0, i - 80) : i + 200]
        compound = "是" if COMPOUND.search(sent) else ""
        src = str(path.relative_to(ROOT)).replace("\\", "/")
        rows.append(
            {
                "book": book_from_path(path, base),
                "juan": juan_from_stem(path.stem),
                "source_kind": "mirror" if "/mirror/" in src else "wiki",
                "source_file": src,
                "match_type": "复合官名" if compound else "含侍中",
                "hint_name": near_name(sent),
                "sentence": sent,
                "status": "待审",
                "person": "",
                "role_note": "",
                "reviewer": "",
            }
        )
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description="Extract 侍中 candidate sentences to CSV")
    p.add_argument("--input", default=str(ROOT / "data" / "raw"))
    p.add_argument("--output", default=str(ROOT / "data" / "candidates" / "shizhong_candidates.csv"))
    args = p.parse_args()

    in_root = Path(args.input)
    if not in_root.is_absolute():
        in_root = ROOT / args.input
    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    files = iter_txt_files(in_root)
    # 不要吃掉 wikitext 同名旁路；只处理 .txt
    all_rows: list[dict] = []
    for f in files:
        if f.suffix.lower() != ".txt":
            continue
        all_rows.extend(extract_file(f, in_root if in_root.is_dir() else in_root.parent))

    fields = [
        "book",
        "juan",
        "source_kind",
        "source_file",
        "match_type",
        "hint_name",
        "sentence",
        "status",
        "person",
        "role_note",
        "reviewer",
    ]
    with out_path.open("w", encoding="utf-8-sig", newline="") as fp:
        w = csv.DictWriter(fp, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)

    print(f"files={len(files)} candidates={len(all_rows)} -> {out_path}")
    if all_rows:
        print("sample:")
        for r in all_rows[:5]:
            print(f"  [{r['book']} 卷{r['juan']}] {r['hint_name'] or '?'} | {r['sentence'][:60]}")


if __name__ == "__main__":
    main()
