"""导出图谱用 JSON：nodes + links（仅双端有 id 的边 + 高度节点）"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "db" / "shizhong.db"
OUT = ROOT / "shizhongdata" / "data" / "graph.json"


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    persons = {}
    for p in cur.execute(
        "SELECT id, name, dynasty_primary, n_terms, n_sources FROM person"
    ):
        persons[p["id"]] = {
            "id": p["id"],
            "name": p["name"],
            "dynasty": p["dynasty_primary"] or "?",
            "n_terms": p["n_terms"] or 0,
            "n_sources": p["n_sources"] or 0,
            "degree": 0,
        }

    links = []
    for r in cur.execute(
        "SELECT from_id, to_id, from_name, to_name, rel_primary FROM relation"
    ):
        a, b = r["from_id"], r["to_id"]
        if not a or not b or a not in persons or b not in persons:
            continue
        if a == b:
            continue
        links.append(
            {
                "source": a,
                "target": b,
                "type": r["rel_primary"] or "关系",
                "label": r["from_name"] + "—" + r["to_name"],
            }
        )
        persons[a]["degree"] += 1
        persons[b]["degree"] + 1

    # 修正 degree
    for p in persons.values():
        p["degree"] = 0
    for e in links:
        persons[e["source"]]["degree"] += 1
        persons[e["target"]]["degree"] += 1

    # 只保留有边的节点 + 关系多的
    linked_ids = set()
    for e in links:
        linked_ids.add(e["source"])
        linked_ids.add(e["target"])
    nodes = [persons[i] for i in linked_ids]
    # 按度排序，便于力导向稳定
    nodes.sort(key=lambda n: -n["degree"])

    payload = {
        "meta": {
            "node_count": len(nodes),
            "link_count": len(links),
            "primary": "#7E0C6E",
        },
        "nodes": nodes,
        "links": links,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print("nodes", len(nodes), "links", len(links), "->", OUT)
    con.close()


if __name__ == "__main__":
    main()
