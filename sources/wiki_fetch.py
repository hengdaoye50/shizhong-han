"""从维基文库拉取古籍卷文，落地为 data/raw/<书名>/<标题>.txt。

支持按书前缀自动发现卷目，处理 429 限速。

用法:
  python sources/wiki_fetch.py --discover 漢書
  python sources/wiki_fetch.py --book 漢書
  python sources/wiki_fetch.py --book 後漢書 --sleep 1.5
  python sources/wiki_fetch.py --book 漢書 --only 068,069
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://zh.wikisource.org/w/api.php"
UA = "ShizhongDB/0.1 (academic research; local fetch)"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def _get(params: dict, timeout: int = 40, retries: int = 5) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    delay = 2.0
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                print(f"  429, sleep {delay:.1f}s", file=sys.stderr)
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            raise
        except TimeoutError:
            if attempt < retries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            raise
    raise RuntimeError("unreachable")


def list_volumes(book: str) -> list[str]:
    """列出 <book>/卷 下全部页面标题。"""
    titles: list[str] = []
    cont: dict | None = None
    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apprefix": f"{book}/卷",
            "aplimit": "50",
            "format": "json",
        }
        if cont:
            params.update(cont)
        d = _get(params)
        titles.extend(x["title"] for x in d.get("query", {}).get("allpages", []))
        if "continue" in d:
            cont = d["continue"]
            time.sleep(1.0)
        else:
            break
    return titles


def filter_titles(titles: list[str], only: str | None) -> list[str]:
    """only='68,069,10上' 时按卷号片段过滤。"""
    if not only:
        return titles
    keys = [k.strip() for k in only.split(",") if k.strip()]
    out = []
    for t in titles:
        # t like 漢書/卷068 or 後漢書/卷10上
        juan = t.rsplit("卷", 1)[-1]
        if juan in keys or juan.lstrip("0") in {k.lstrip("0") for k in keys}:
            out.append(t)
    return out


def safe_name(title: str) -> str:
    # 漢書/卷001上 -> 卷001上
    return title.rsplit("/", 1)[-1].replace("/", "_")


def strip_wikitext(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\{\{[*]\|([^{}]*)\}\}", r"（注：\1）", text)
    text = re.sub(r"\{\{(gap|Textquality|header2|footer|東漢作品|onlyinclude)[^}]*\}\}", "", text)
    text = re.sub(r"\{\{YL\|([^}|]+)(?:\|[^}]*)?\}\}", r"【\1】", text)
    text = re.sub(r"\{\{blue\|", "", text)
    text = re.sub(r"\{\{red\|", "", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"'''+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def fetch_one(title: str) -> str:
    d = _get(
        {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
        }
    )
    if "error" in d:
        raise RuntimeError(d["error"].get("info", str(d["error"])))
    return d["parse"]["wikitext"]


def fetch_book(book: str, titles: list[str], sleep: float) -> tuple[int, int]:
    dest = RAW / book
    dest.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for i, title in enumerate(titles, 1):
        name = safe_name(title)
        plain = dest / f"{name}.txt"
        rawp = dest / f"{name}.wikitext"
        if plain.exists() and rawp.exists():
            print(f"[{i}/{len(titles)}] skip {title}")
            ok += 1
            continue
        try:
            wt = fetch_one(title)
        except Exception as e:  # noqa: BLE001
            print(f"[{i}/{len(titles)}] FAIL {title}: {e}", file=sys.stderr)
            fail += 1
            time.sleep(sleep)
            continue
        rawp.write_text(wt, encoding="utf-8")
        plain.write_text(strip_wikitext(wt), encoding="utf-8")
        print(f"[{i}/{len(titles)}] ok {title} {len(wt)}")
        ok += 1
        time.sleep(sleep)
    return ok, fail


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--discover", help="仅列出该书卷目后退出")
    p.add_argument("--book", help="拉取该书全部（或 --only 过滤后）卷目")
    p.add_argument("--only", help="卷号过滤，逗号分隔，如 68,69,10上")
    p.add_argument("--sleep", type=float, default=1.2)
    args = p.parse_args()

    if args.discover:
        ts = list_volumes(args.discover)
        print(f"{args.discover}: {len(ts)} volumes")
        for t in ts:
            print(t)
        return

    if not args.book:
        p.error("需要 --book 或 --discover")

    titles = list_volumes(args.book)
    titles = filter_titles(titles, args.only)
    print(f"{args.book}: {len(titles)} volumes to fetch, sleep={args.sleep}")
    ok, fail = fetch_book(args.book, titles, sleep=args.sleep)
    print(f"done ok={ok} fail={fail} -> {RAW / args.book}")


if __name__ == "__main__":
    main()
