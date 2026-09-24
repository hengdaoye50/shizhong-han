# -*- coding: utf-8 -*-
"""汇总 enrich_raw_hits 拒项，出人工审定表。"""
import json
import re
from pathlib import Path
from collections import Counter

ROOT = Path(r"D:\CODEX\两汉侍中数据库搭建")
SRC = ROOT / "data" / "candidates" / "enrich_raw_hits.json"
OUT = ROOT / "data" / "candidates" / "enrich_reject_review.json"
OUT_MD = ROOT / "docs" / "enrich_reject_review.md"

FLAG_SNIP = re.compile(r".{0,35}侍中.{0,45}")


def snippet(window: str) -> str:
    m = FLAG_SNIP.search(window or "")
    return (m.group(0) if m else (window or "")[:80]).replace("\n", " ").strip()


def heuristic(x: dict) -> str:
    name = x.get("name") or ""
    w = x.get("window") or ""
    sn = snippet(w)
    # 他传/邻传：窗口内出现「==某人==」章节标记且姓名不在该段主语位
    if re.search(r"==+[^=]{1,8}==+", w) and name not in sn[:20]:
        return "疑邻传/他传句"
    if name not in w:
        return "姓名未见于窗口"
    # 姓名仅出现在窗口边缘，侍中句主语更像他人
    idx = w.find("侍中")
    nidx = w.find(name)
    if 0 <= nidx and 0 <= idx and abs(nidx - idx) > 40:
        return "姓名与侍中句距离远"
    if "稍遷侍中" in w or "迁侍中" in w or "遷侍中" in w:
        return "有「迁侍中」字样，待核主语"
    return "待核"


def main():
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    out = []
    for i, x in enumerate(rows):
        sn = snippet(x.get("window", ""))
        reason = heuristic(x)
        out.append(
            {
                "n": i + 1,
                "id": x.get("id"),
                "name": x.get("name"),
                "dynasty": x.get("dynasty"),
                "book": x.get("book"),
                "juan": x.get("juan"),
                "snippet": sn,
                "heuristic": reason,
                "window": x.get("window"),
            }
        )
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# enrich 拒项人工审定表", "", f"共 **{len(out)}** 条。源：`data/candidates/enrich_raw_hits.json`。", ""]
    lines.append("启发式分类：" + ", ".join(f"{k}×{v}" for k, v in Counter(r["heuristic"] for r in out).most_common()))
    lines.append("")
    lines.append("| # | ID | 人物 | 朝代 | 出处 | 摘句 | 启发式 | 建议 |")
    lines.append("|---|----|------|------|------|------|--------|------|")
    for r in out:
        sug = "维持拒收" if r["heuristic"] in ("疑邻传/他传句", "姓名未见于窗口") else "可议"
        sn = r["snippet"][:48].replace("|", "\\|")
        lines.append(
            f"| {r['n']} | {r['id']} | {r['name']} | {r['dynasty']} | {r['book']}{r['juan']} | {sn} | {r['heuristic']} | {sug} |"
        )
    lines.append("")
    lines.append("## 审定说明")
    lines.append("- **维持拒收**：窗口属邻传/他传，或姓名未在句中作主语，不入 sources。")
    lines.append("- **可议**：可能为主语误判漏收，需人工读上下文定夺。")
    lines.append("- 三态原则不变：无明文不得升格为「有明文」。")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("COUNT", len(out))
    print("WROTE", OUT)
    print("WROTE", OUT_MD)
    for r in out[:12]:
        print(f"{r['n']}|{r['id']}|{r['name']}|{r['heuristic']}|{r['snippet'][:40]}")


if __name__ == "__main__":
    main()
