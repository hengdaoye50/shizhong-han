"""收尾：合并 frontmatter 中同一 sources 条目下的重复 quote 行。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hans import norm_quote

CARDS = Path(__file__).resolve().parents[1] / "data" / "cards"

fixed = 0
for p in sorted(CARDS.glob("*.md")):
    t = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", t, re.S)
    if not m:
        continue
    fm, body = m.group(1), m.group(2)
    lines = fm.splitlines(keepends=True)
    out = []
    i = 0
    changed = False
    while i < len(lines):
        ln = lines[i]
        out.append(ln)
        # 收集紧随其后的连续 quote 行
        if re.match(r"^\s+quote:", ln):
            quotes = [ln]
            j = i + 1
            while j < len(lines) and re.match(r"^\s+quote:", lines[j]):
                quotes.append(lines[j])
                j += 1
            if len(quotes) > 1:
                # 只保留第一条 quote，其余丢弃（内容已归一相同或近同）
                # 用 norm_quote 判定：若归一后相同则丢后面的；不同则保留为独立条目不在此处理
                first_q = re.sub(r".*quote:\s*", "", quotes[0]).strip()
                keep = [quotes[0]]
                seen = {norm_quote(first_q)}
                for q in quotes[1:]:
                    qq = re.sub(r".*quote:\s*", "", q).strip()
                    k = norm_quote(qq)
                    if k in seen:
                        changed = True
                        continue
                    seen.add(k)
                    keep.append(q)
                # 替换：去掉已 append 的第一条，重新写 keep
                out.pop()
                out.extend(keep)
                i = j
                continue
        i += 1
    if changed:
        p.write_text(f"---\n{''.join(out)}\n---\n{body}", encoding="utf-8")
        fixed += 1

print("cards quote-deduped", fixed)
