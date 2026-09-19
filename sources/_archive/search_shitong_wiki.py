"""检索维基文库：十通/类书中与侍中职官相关的页面。"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://zh.wikisource.org/w/api.php"
UA = "ShizhongDB/0.1 (academic research; local fetch)"


def api(params: dict, retries: int = 4) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    delay = 2.0
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 20)
                continue
            if e.code == 404:
                return {"error": {"code": "missing"}}
            raise
        except TimeoutError:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise
    raise RuntimeError("unreachable")


def opensearch(q: str, limit: int = 10) -> list[str]:
    d = api({"action": "opensearch", "limit": limit, "format": "json", "search": q})
    return d[1] if len(d) > 1 else []


def allpages(prefix: str, limit: int = 50) -> list[str]:
    titles = []
    cont = None
    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apprefix": prefix,
            "aplimit": str(limit),
            "format": "json",
        }
        if cont:
            params.update(cont)
        d = api(params)
        titles.extend(x["title"] for x in d.get("query", {}).get("allpages", []))
        if "continue" in d:
            cont = d["continue"]
            time.sleep(0.8)
        else:
            break
        if len(titles) > 400:
            break
    return titles


def main():
    queries = [
        "通典 職官",
        "通典 职官",
        "文獻通考 職官",
        "文献通考 职官",
        "通志 職官",
        "續通典 職官",
        "唐六典",
        "冊府元龜 職官",
        "玉海 職官",
        "通典/卷",
        "文獻通考/卷",
        "唐六典/卷",
    ]
    print("=== opensearch ===")
    for q in queries:
        try:
            hits = opensearch(q, 8)
        except Exception as e:
            print(q, "ERR", e)
            time.sleep(1.5)
            continue
        print(f"\n{q} ->")
        for h in hits:
            print("  ", h)
        time.sleep(1.8)

    print("\n=== allpages prefixes ===")
    prefixes = [
        "通典/",
        "通典·",
        "文獻通考/",
        "文献通考/",
        "通志/",
        "唐六典/",
        "續通典/",
        "續文獻通考/",
        "冊府元龜/",
        "玉海/",
    ]
    for pref in prefixes:
        try:
            titles = allpages(pref)
        except Exception as e:
            print(pref, "ERR", e)
            time.sleep(1.5)
            continue
        print(f"\n{pref} count={len(titles)}")
        for t in titles[:25]:
            print("  ", t)
        if len(titles) > 25:
            print("  ...")
        time.sleep(2.0)


if __name__ == "__main__":
    main()
