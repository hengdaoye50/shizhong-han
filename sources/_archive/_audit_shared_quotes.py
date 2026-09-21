"""交叉比对：共享 quote 卡片 + 引文主语与卡名不符。"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CARDS = ROOT / "data" / "cards"
sys_path = ROOT / "sources"
import sys

sys.path.insert(0, str(sys_path))
from hans import norm_quote, t2s  # noqa: E402


def parse(p: Path):
    t = p.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    if not m:
        return None
    fm = m.group(1)
    name = re.search(r"^name:\s*(.*)$", fm, re.M)
    quotes = re.findall(r"quote:\s*(.+)", fm)
    dyn = re.search(r"^dynasty:\s*(.*)$", fm, re.M)
    return {
        "file": p.name,
        "name": name.group(1).strip() if name else "",
        "dynasty": dyn.group(1).strip() if dyn else "",
        "quotes": quotes,
    }


def main() -> None:
    cards = [c for c in (parse(p) for p in sorted(CARDS.glob("*.md"))) if c]
    by_q = defaultdict(list)
    for c in cards:
        for q in c["quotes"]:
            key = norm_quote(t2s(q.strip().strip("「」")))
            if len(key) >= 8:
                by_q[key].append(c["name"] or c["file"])

    print("=== quotes shared by >1 person card ===")
    for key, names in sorted(by_q.items(), key=lambda x: -len(set(x[1]))):
        uniq = sorted(set(names))
        if len(uniq) <= 1:
            continue
        # 家族并列（汤融/千秋延寿/弘阊）可接受，但仍列出供审
        print(f"[{len(uniq)}人] {uniq}")
        print("   ", key[:90])

    # 卡名不在引文、且引文含明确第三人名+侍中
    print("\n=== likely third-party quotes (name absent, others present) ===")
    other = re.compile(
        r"(刘昆|杜乔|周栩|冯羨|栾巴|张綱|郭遵|刘班|宋登|刘珍|张纯|张凭|"
        r"卫青|朱买臣|严助|何休|萧育|张玄|丁恭|淳于恭|荀顗|和嶠|"
        r"详|综|蔡邕|种辑|種辑|王粲|刘放|孙资|金敞|霍光|"
        r"歆长子|珍与|凭虎贲|登明识|纯少|泰为尚书|青为建章|买臣|"
        r"引见极日|岁余复征|岁余复徵|十八年，以病|察孝廉，举高第)"
    )
    for c in cards:
        name = c["name"]
        base = re.sub(r"[（(].*?[)）]", "", name).strip()
        if not base:
            continue
        joined = " ".join(c["quotes"])
        # traditional variants
        alts = {base, base.replace("台", "臺"), base.replace("种", "種"),
                base.replace("阚", "闞"), base.replace("刘", "劉"),
                base.replace("卫", "衞"), base.replace("钱", "錢")}
        hit = any(a and a in joined for a in alts)
        if hit:
            continue
        # single-char given name hit (茂/璩/举)
        if len(base) >= 2 and base[1:] in joined:
            continue
        m = other.search(joined)
        if m:
            print(f"{c['file']} name={name} → 可疑他称「{m.group(1)}」 | {joined[:70]}")


if __name__ == "__main__":
    main()
