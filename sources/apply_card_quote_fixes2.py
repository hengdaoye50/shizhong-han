"""二次修正：是仪 / 张兴 / 张霸 错挂引文。"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import t2s

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "data" / "cards"


def find(name: str) -> Path | None:
    hits = list(CARDS.glob(f"{name}_*.md"))
    return hits[0] if hits else None


def fix(name: str, remove_pats: list[str], note: str, nature: str | None = None) -> None:
    p = find(name)
    if not p:
        print("MISS", name)
        return
    raw = p.read_text(encoding="utf-8")
    orig = raw
    lines = []
    for ln in raw.splitlines(keepends=True):
        if re.match(r"^\s*quote:", ln):
            t = re.sub(r".*quote:\s*", "", ln)
            if any(x in t or x in t2s(t) for x in remove_pats):
                continue
        lines.append(ln)
    raw = "".join(lines)
    if nature and re.search(r"^    nature:\s*.*$", raw, re.M):
        raw = re.sub(
            r"^    nature:\s*.*$",
            f"    nature: {t2s(nature)}",
            raw,
            count=1,
            flags=re.M,
        )
    if "## 校录备注" in raw:
        raw = re.sub(
            r"(## 校录备注\n)",
            r"\1\n- " + t2s(note) + "（卡源审计修正）\n",
            raw,
            count=1,
        )
    else:
        raw = raw.rstrip() + f"\n\n## 校录备注\n\n- {t2s(note)}（卡源审计修正）\n"
    if raw != orig:
        p.write_text(raw, encoding="utf-8")
        print("FIX", name)
    else:
        print("same", name)


fix(
    "是仪",
    ["详、综", "詳、綜", "并为侍中", "权下都建业", "权下都建业"],
    "原挂「详、综并为侍中」，非是仪本传；是仪仕履以吴书本传为准，侍中任职待考",
    nature="吴臣（详综句已剔除；侍中任职待考）",
)
fix("张兴", ["帝善之，拜为侍中", "数进见"], "「帝善之拜为侍中」不挂张兴")
fix("张霸", ["八年，复为侍中", "领骑都尉"], "「八年复为侍中」与郑弘条重叠，暂去挂靠待核")
