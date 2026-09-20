"""按人工审定把 enrich 候选句追加进 data/cards/（去重后写 sources）。

用法:
  python sources/apply_enrich_raw_hits.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import norm_quote, t2s

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"

# 2026-09 人工审定：仅写入下列人名的指定句（简体）
# 拒项与霍山弱证不在此表
APPROVED: dict[str, list[tuple[str, str, str]]] = {
    # name: (book, juan, quote)  quote 用简体
    "淳于恭": [
        ("后汉书", "卷3", "侍中淳于恭奏，帝亲称制临决，如孝宣甘露石渠故事"),
        ("后汉书", "卷79下", "时会京师诸儒于白虎观，讲论五经同异……侍中淳于恭奏之，帝亲临称制，如石渠故事"),
    ],
    "史丹": [
        ("汉书", "卷010", "赖侍中史丹护太子家，辅助有力，上亦以先帝尤爱太子，故得无废"),
        ("汉书", "卷098", "时凤在位，与皇太子同心忧惧，刺侍中史丹拥右太子，语在丹传"),
    ],
    "史恃": [
        ("后汉纪", "卷028", "诏使侍中史恃、太仆韩融告张济曰：朕惟宗庙之重……"),
    ],
    "和逌": [
        ("三国志", "卷04", "侍中和逌、尚书陈骞等作诗稽留，有司奏免官"),
    ],
    "王能": [
        ("汉书", "卷019", "卫尉王能为侍中光禄勋，二年贬为弘农，坐吕宽自杀"),
    ],
    "王方": [
        ("后汉书", "卷25", "会诏百官举贤良方正，恭荐中牟名士王方，帝即徵方诣公车……方致位侍中"),
    ],
    "王接": [
        ("汉书", "卷019", "九月戊子，侍中卫尉王接为大司马车骑将军"),
    ],
    "王音": [
        ("汉书", "卷019", "侍中中郎将王音为太仆，三年迁"),
    ],
    "郭攸之": [
        ("三国志", "卷35", "侍中郭攸之、费祎、侍郎董允等，先帝简拔以遗陛下，至于斟酌规益，进尽忠言，则其任也"),
    ],
    "傅嘉": [
        ("汉书", "卷081", "前为侍中，毁谮仁贤，诬诉大臣，令俊艾者久失其位……其免嘉为庶人"),
    ],
    "荀勖": [
        ("三国志", "卷35", "侍中领中书监济北侯臣荀勖、中书令关内侯臣和峤奏：使臣定故蜀丞相诸葛亮故事"),
    ],
    "李仁": [
        ("三国志", "卷48", "吴平后，晋侍中庾峻等问皓侍中李仁曰：闻吴主披人面，刖人足，有诸乎"),
    ],
    "郤巡": [
        ("后汉书", "卷82上", "陈郡郤巡，学传英业，官至侍中"),
    ],
    # 可选：去重后写入
    "王林卿": [
        ("汉书", "卷077", "初，邛成太后外家王氏贵，而侍中王林卿通轻侠，倾京师"),
    ],
    "王莽": [
        ("汉书", "卷010", "封舅曼子侍中骑都尉光禄大夫王莽为新都侯"),
        ("汉书", "卷019", "十一月丙寅，侍中骑都尉光禄大夫王莽为大司马"),
    ],
    "蔡邕": [
        ("三国志", "卷06", "卓怒，罢坐，欲诛植，侍中蔡邕劝之，得免"),
    ],
    "金敞": [
        ("汉书", "卷036", "与侍中金敞拾遗于左右"),
        ("汉书", "卷019", "侍中奉车都尉金敞为水衡都尉，一年迁"),
    ],
}


def find_card(name: str) -> Path | None:
    hits = list(CARDS.glob(f"{name}_*.md"))
    return hits[0] if hits else None


def existing_quotes(text: str) -> set[str]:
    keys = set()
    for m in re.finditer(r"quote:\s*(.+)", text):
        q = m.group(1).strip().strip("「」")
        keys.add(norm_quote(q))
        keys.add(norm_quote(t2s(q)))
    return keys


def append_sources(path: Path, entries: list[tuple[str, str, str]]) -> int:
    raw = path.read_text(encoding="utf-8")
    seen = existing_quotes(raw)
    add_block = ""
    n = 0
    for book, juan, quote in entries:
        s = t2s(quote)
        if norm_quote(s) in seen:
            continue
        add_block += f"  - book: {t2s(book)}\n    juan: {t2s(juan)}\n    quote: 「{s}」\n"
        seen.add(norm_quote(s))
        n += 1
    if not n:
        return 0
    # 在 frontmatter 的 sources 段末尾、下一个顶栏字段前插入
    m = re.search(r"(sources:\n(?:[ \t].*\n|\n)*)", raw)
    if not m:
        # 若无 sources，插在 --- 前
        m2 = re.search(r"\n---\n", raw)
        if not m2:
            raise SystemExit(f"no frontmatter end: {path.name}")
        raw = raw[: m2.start()] + "\nsources:\n" + add_block + raw[m2.start() :]
    else:
        raw = raw[: m.end()] + add_block + raw[m.end() :]
    path.write_text(raw, encoding="utf-8")
    return n


def main() -> None:
    total = 0
    for name, entries in APPROVED.items():
        p = find_card(name)
        if not p:
            print("MISS", name)
            continue
        n = append_sources(p, entries)
        total += n
        print(f"{name:6s} +{n}  {p.name}")
    print("added quotes total", total)


if __name__ == "__main__":
    main()
