"""在 GitHub 检索两汉职官/侍中相关开源电子文本（合法镜像，不爬 ctext）。"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "ShizhongDB/0.1 (academic research; local fetch)"
OUT = Path(r"D:\CODEX\两汉侍中数据库搭建\data\candidates\github_corpus_search.json")


def gh(url: str, retries: int = 3):
    delay = 3.0
    for attempt in range(retries):
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < retries - 1:
                print(f"  rate/sleep {delay}s", flush=True)
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except TimeoutError:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise
    return None


QUERIES = [
    "漢官六種",
    "汉官六种",
    "通志 職官",
    "通志 职官",
    "居延漢簡",
    "居延汉简",
    "尹灣漢簡",
    "尹湾汉简",
    "張家山漢簡",
    "张家山汉简",
    "懸泉漢簡",
    "汉简 释文",
    "侍中 漢",
    "十通 通典",
    "通典 杜佑",
    "文獻通考",
    "职官分纪",
    "历代职官表",
    "冊府元龜",
    "太平御覽 侍中",
    "四庫全書 職官",
    "chinese classics 四库",
    "chinese historical texts open",
    "guwen guoxue database",
    "ctext mirror open",
    "chinese-text-project",
    "漢書 百官",
    "續漢書 百官",
    "兩漢會要",
    "西汉会要 东汉会要",
    "敦煌 漢簡 職官",
    "秦漢簡牘 釋文",
    "open chinese historical corpus",
    "chinese_bert 汉籍",
    "殆知阁",
    "daizhigev",
    "kanripo 漢官",
    "kanripo 通典",
    "kanripo 職官",
    "古籍 整理 txt 漢書",
    "二十四史 txt github",
]


def main():
    hits = []
    for q in QUERIES:
        url = (
            "https://api.github.com/search/repositories?q="
            + urllib.parse.quote(q)
            + "&sort=stars&order=desc&per_page=8"
        )
        print(f"\n== {q}")
        try:
            d = gh(url)
        except Exception as e:
            print("  ERR", e)
            hits.append({"query": q, "error": str(e)})
            time.sleep(2)
            continue
        if not d:
            hits.append({"query": q, "error": "empty"})
            time.sleep(2)
            continue
        items = d.get("items") or []
        print("  total", d.get("total_count"), "shown", len(items))
        for it in items:
            rec = {
                "query": q,
                "full_name": it["full_name"],
                "description": (it.get("description") or "")[:120],
                "stars": it.get("stargazers_count"),
                "html_url": it.get("html_url"),
                "updated_at": it.get("updated_at"),
            }
            print(f"  {rec['full_name']} ★{rec['stars']} | {rec['description'][:70]}")
            hits.append(rec)
        time.sleep(2.5)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nwrote", OUT, "records", len(hits))


if __name__ == "__main__":
    main()
