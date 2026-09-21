"""修正人物卡中错挂的 sources 引文（名实不符 / 他传误并）。"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import norm_quote, t2s

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"

# 按卡名：删除 quote 子串（简体/原繁都匹配 norm 后）；可选追加正确 sources
FIX: dict[str, dict] = {
    "何休": {
        "remove": ["岁余复征", "岁余复徵", "再迁侍中，卒于官"],
        "note": "「岁余复征再迁侍中」出儒林下「育」条，非何休本传；何休与侍中系连待考",
    },
    "张玄": {
        "remove": ["岁余复征", "岁余复徵", "再迁侍中，卒于官"],
        "note": "同句多卡误挂，非张玄本传确证",
    },
    "萧育": {
        "remove": ["岁余复征", "岁余复徵", "再迁侍中，卒于官"],
        "note": "同句多卡误挂",
    },
    "孔昱": {
        "remove": ["察孝廉，举高第，三迁侍中"],
        "note": "「三迁侍中」本传明文属刘儒；孔昱本传为方正/洛阳令等",
    },
    "贾彪": {
        "remove": ["察孝廉，举高第，三迁侍中"],
        "note": "同句本传属刘儒",
    },
    "陈翔": {
        "remove": ["察孝廉，举高第，三迁侍中"],
        "note": "陈翔本传为侍御史/刺史，未见三迁侍中明文",
    },
    "关统": {
        "remove": ["弱冠为侍中", "中監军", "中监军"],
        "add": [
            {
                "book": "三国志",
                "juan": "蜀书·关张马黄赵传",
                "quote": "子统嗣，尚公主，官至虎贲中郎将。卒，无子，以兴庶子彝续封",
            }
        ],
        "nature": "关兴子嗣；尚公主，官至虎贲中郎将（非侍中）",
        "note": "侍中中监军属关兴，非关统",
    },
    "关兴": {
        "remove": [],
        "add": [
            {
                "book": "三国志",
                "juan": "蜀书·关张马黄赵传",
                "quote": "关兴字安国，少有令问，丞相诸葛亮深器异之。弱冠为侍中、中监军，数岁卒",
            }
        ],
        "nature": "弱冠为侍中、中监军（蜀汉）",
        "note": "本传明文",
    },
    "宋弘": {
        "remove": ["純少襲爵士", "纯少袭爵士", "哀、平间为侍中，王莽时至列卿"],
        "add": [
            {
                "book": "后汉书",
                "juan": "伏侯宋蔡冯赵牟韦列传",
                "quote": "宋弘字仲子，京兆长安人也……弘少而温顺，哀、平间作侍中，王莽时为共工",
            }
        ],
        "nature": "哀、平间作侍中；王莽时为共工",
        "note": "原挂张纯句，已换宋弘本传",
    },
    "陈矫": {
        "remove": ["后徵泰为尚书右仆射", "徵泰为尚书"],
        "add": [
            {
                "book": "三国志",
                "juan": "魏书·桓二陈徐卫卢传",
                "quote": "陈矫字季弼，广陵东阳人也……加侍中光禄大夫，迁司徒",
            }
        ],
        "nature": "魏：加侍中光禄大夫，迁司徒",
        "note": "原挂陈泰句",
    },
    "郑均": {
        "remove": ["建和初", "四府表荐", "侍讲禁内，再迁为侍中", "侍讲宫中，再迁为侍中"],
        "note": "建和初条本传属赵典；郑均与赵典条勿混",
    },
    "李尤": {
        "remove": ["诏珍与", "永宁元年，太后又诏珍", "建武已来名臣传"],
        "note": "永宁元年诏珍撰传属刘珍；李尤详文苑本传",
    },
    "江革": {
        "remove": ["引见极日", "引见極日", "访以政事，迁侍中骑都尉"],
        "note": "「引见极日…迁侍中骑都尉」本传属淳于恭",
    },
    "尹敏": {
        "remove": [
            "顺帝以登明识礼乐",
            "擢拜侍中，典领秘书近署",
            "转拜侍中",
        ],
        "note": "「登明识礼乐」属宋登；「典领秘书近署」属张驯",
    },
    "孙期": {
        "remove": ["拜凭虎贲中郎将", "以侍中兼领之", "解遵禁锢"],
        "note": "张凭句误挂；孙期本传举方正、终于家，侍中任职待考",
    },
    "张兴": {
        "remove": ["拜凭虎贲中郎将", "以侍中兼领之", "解遵禁锢"],
        "note": "张凭句误挂",
    },
    "戴凭": {
        "remove": ["拜凭虎贲中郎将", "以侍中兼领之", "解遵禁锢"],
        "add": [
            {
                "book": "职官分纪",
                "juan": "门下省·侍中（引东观汉记）",
                "quote": "东观汉记：戴冯（凭）为侍中，正旦朝会……京师为之语曰：解经不穷戴侍中",
            }
        ],
        "nature": "光武时侍中；解经不穷戴侍中",
        "note": "去掉张凭句，补东观/职官分纪系戴凭明文",
    },
    "杨政": {
        "remove": ["帝善之，拜为侍中", "数进见問得失", "数进见问得失"],
        "note": "「帝善之拜为侍中」更近戴凭/公孙晖类，不挂杨政",
    },
    "钟兴": {
        "remove": ["十八年，以病乞身", "为侍中骑都尉，卒于官"],
        "add": [
            {
                "book": "后汉书",
                "juan": "儒林列传下",
                "quote": "钟兴字次文，汝南汝阳人也。少从少府丁恭受《严氏春秋》……帝善之，拜郎中，稍迁左中郎将……卒于官",
            }
        ],
        "nature": "光武时经学家；拜郎中/左中郎将（侍中任职待考）",
        "note": "「十八年以病乞身」本传属周泽",
    },
    "许慎": {
        "remove": ["迁侍中，出为弘农太守"],
        "add": [
            {
                "book": "后汉书",
                "juan": "儒林列传下",
                "quote": "许慎字叔重，汝南召陵人也……为郡功曹，举孝廉，再迁除洨长。卒于家",
            }
        ],
        "nature": "经学家（五经无双）；侍中任职待考",
        "note": "原挂蔡玄句",
    },
    "张玄": {
        "remove": ["岁余复征", "岁余复徵", "再迁侍中，卒于官"],
        "add": [
            {
                "book": "后汉书",
                "juan": "儒林列传下",
                "quote": "张玄字君夏，河内河阳人也。少习《颜氏春秋》，兼通数家法……",
            }
        ],
        "nature": "东汉儒林；侍中任职待考（勿用他传「岁余复征」句）",
        "note": "见上",
    },
}


def find(name: str) -> Path | None:
    hits = list(CARDS.glob(f"{name}_*.md"))
    return hits[0] if hits else None


def strip_quotes(raw: str, patterns: list[str]) -> str:
    if not patterns:
        return raw
    lines = raw.splitlines(keepends=True)
    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if re.match(r"^\s*quote:\s*", ln):
            # gather this quote line only (single line quotes in this corpus)
            text = re.sub(r".*quote:\s*", "", ln)
            tnorm = t2s(text)
            if any(p in text or p in tnorm or norm_quote(p) in norm_quote(tnorm) for p in patterns):
                i += 1
                continue
        out.append(ln)
        i += 1
    return "".join(out)


def add_sources(raw: str, items: list[dict]) -> str:
    if not items:
        return raw
    block = ""
    for it in items:
        block += (
            f"  - book: {t2s(it['book'])}\n"
            f"    juan: {t2s(it['juan'])}\n"
            f"    quote: 「{t2s(it['quote'])}」\n"
        )
    m = re.search(r"(sources:\n(?:[ \t].*\n|\n)*)", raw)
    if not m:
        return raw
    return raw[: m.end()] + block + raw[m.end() :]


def set_nature(raw: str, nature: str) -> str:
    if re.search(r"^    nature:\s*.*$", raw, re.M):
        return re.sub(r"^    nature:\s*.*$", f"    nature: {t2s(nature)}", raw, count=1, flags=re.M)
    return raw


def append_note(raw: str, note: str) -> str:
    if "## 校录备注" in raw:
        return re.sub(r"(## 校录备注\n)", r"\1\n- " + t2s(note) + "\n", raw, count=1)
    return raw.rstrip() + f"\n\n## 校录备注\n\n- {t2s(note)}\n"


def main() -> None:
    for name, cfg in FIX.items():
        p = find(name)
        if not p:
            print("MISS", name)
            continue
        raw = p.read_text(encoding="utf-8")
        raw2 = strip_quotes(raw, cfg.get("remove") or [])
        if cfg.get("add"):
            raw2 = add_sources(raw2, cfg["add"])
        if cfg.get("nature"):
            raw2 = set_nature(raw2, cfg["nature"])
        if cfg.get("note"):
            raw2 = append_note(raw2, cfg["note"] + "（卡源审计修正）")
        if raw2 != raw:
            p.write_text(raw2, encoding="utf-8")
            print("FIX", name, p.name)
        else:
            print("same", name)


if __name__ == "__main__":
    main()
