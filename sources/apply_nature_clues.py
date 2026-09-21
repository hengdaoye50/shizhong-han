"""按卡片 sources 原典，仅对下列人回填 shizhong_terms.nature 年代线索。

原则：只写能在该卡 quote 或可靠同源摘句中核验的表述；不造年号。
误项（郭昌、李尤「建武」、郑均「建和」、王歙「光武」）一并纠正。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import t2s

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"

# name -> new nature（简体；须与 sources 一致）
NATURE: dict[str, str] = {
    "丁冲": "建安元年为侍中（与伏完、种辑等同封列侯）",
    "关统": "弱冠为侍中、中监军（蜀汉）",
    "周举": "拜为侍中，与杜乔等八使巡行",
    "史恃": "献帝时侍中；奉诏告张济",
    "孔安国": "武帝时侍中；特听掌御唾壶",
    "张辟疆": "惠帝崩后（吕后初）年十五为侍中",
    "卓茂": "更始立为侍中祭酒",
    "卫觊": "魏国既建拜侍中（与王粲典制度）",
    "孙资": "青龙初加侍中；曹爽诛后复为侍中领中书令",
    "辛毗": "魏文帝时侍中（谏徙冀州、议猎）",
    "金建": "昭帝时侍中（与兄赏俱）",
    "李祯": "李傕秉政时为侍中（傕州里）",
    "梁安国": "延光中为侍中，有罪免",
    "淳于恭": "建初中侍中（白虎观奏上）；后迁侍中骑都尉",
    "王莽": "成帝时侍中骑都尉光禄大夫；后为大司马",
    "王音": "成帝时侍中中郎将；后迁太仆、御史大夫",
    "金赏": "昭帝时侍中太仆（与建俱侍中）",
    "荀勖": "魏晋间侍中领中书监（奏定诸葛亮故事）",
    "陈泰": "魏：徵为尚书右仆射，加侍中光禄大夫",
    "马何罗": "武帝时侍中仆射；谋反被诛",
    "王接": "侍中卫尉，后为大司马车骑将军（公卿表）",
    # 纠误
    "王歙": "更始时侍中（从入关，封元氏王）",
    "李尤": "侍中；文苑（东汉，与东观撰述相关；非建武时）",
    "郑均": "光武—明帝时侍中（以廉洁称；勿与赵典建和初条混）",
    "郭昌": "任职待考（卡内摘句或系卫青，不作定说）",
}


def find_card(name: str) -> Path | None:
    hits = list(CARDS.glob(f"{name}_*.md"))
    return hits[0] if hits else None


def set_nature(path: Path, nature: str) -> str:
    raw = path.read_text(encoding="utf-8")
    new_nat = t2s(nature)
    m = re.search(r"^---\n(.*?)\n---\n", raw, re.S)
    if not m:
        raise SystemExit(f"no fm {path.name}")
    fm = m.group(1)
    if re.search(r"^    nature:\s*.*$", fm, re.M):
        fm2 = re.sub(r"^    nature:\s*.*$", f"    nature: {new_nat}", fm, count=1, flags=re.M)
    elif re.search(r"^  - start:.*$", fm, re.M):
        # insert nature after first term start/end
        fm2 = re.sub(
            r"^(  - start:.*\n(?:    .*\n)*)",
            r"\1" + f"    nature: {new_nat}\n",
            fm,
            count=1,
            flags=re.M,
        )
    else:
        raise SystemExit(f"no nature slot {path.name}")
    path.write_text(raw[: m.start(1)] + fm2 + raw[m.end(1) :], encoding="utf-8")
    return new_nat


def main() -> None:
    for name, nat in NATURE.items():
        p = find_card(name)
        if not p:
            print("MISS", name)
            continue
        got = set_nature(p, nat)
        print(f"{name}: {got}")


if __name__ == "__main__":
    main()
