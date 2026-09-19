"""从维基文库拉取制度典章相关文本（漢官儀/獨斷/漢官舊儀/会要等）。

用法:
  python sources/fetch_institution_sources.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
API = "https://zh.wikisource.org/w/api.php"
UA = "ShizhongDB/0.1 (academic research; local fetch)"

# 目标页面：维基文库标题 -> 本地书名
TARGETS = {
    "漢官儀": "漢官儀",
    "獨斷": "獨斷",
    "獨斷 (四庫全書本)/卷上": "獨斷",
    "獨斷 (四庫全書本)/卷下": "獨斷",
    "漢官舊儀 (四庫全書本)/卷上": "漢官舊儀",
    "漢官舊儀 (四庫全書本)/卷下": "漢官舊儀",
    "西漢會要/卷01": "西漢會要",
    "西漢會要/卷05": "西漢會要",
    "西漢會要/卷12": "西漢會要",
    "西漢會要/卷13": "西漢會要",
    "西漢會要/卷14": "西漢會要",
    "西漢會要/卷23": "西漢會要",
    "西漢會要/卷24": "西漢會要",
    "西漢會要/卷68": "西漢會要",
}

# 会要职官相关卷（东汉，标题用㑹）
for i in [1, 11, 19, 21, 26, 31, 39]:
    TARGETS[f"東漢㑹要 (四庫全書本)/卷{i:02d}"] = "東漢會要"


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
            raise
        except TimeoutError:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise
    raise RuntimeError("unreachable")


def fetch_page(title: str) -> str | None:
    d = api(
        {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json",
            "formatversion": "2",
        }
    )
    if "error" in d:
        return None
    return d.get("parse", {}).get("wikitext") or None


def to_plain(wikitext: str) -> str:
    t = wikitext
    t = re.sub(r"\{\{[^}]{0,300}\}\}", " ", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", " ", t, flags=re.S)
    t = re.sub(r"<ref[^/]*/>", " ", t)
    t = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]+)\]\]", r"\1", t)
    t = re.sub(r"'''?", "", t)
    t = re.sub(r"={2,}", "\n", t)
    return t.strip() + "\n"


def slug(title: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", title)


def main() -> None:
    saved = 0
    for title, book in TARGETS.items():
        out_dir = RAW / book
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{slug(title)}.txt"
        if out.exists() and out.stat().st_size > 200:
            print(f"skip {title}")
            continue
        try:
            wt = fetch_page(title)
        except Exception as e:
            print(f"FAIL {title}: {e}")
            time.sleep(2)
            continue
        if not wt:
            print(f"empty {title}")
            time.sleep(1.2)
            continue
        plain = to_plain(wt)
        out.write_text(plain, encoding="utf-8")
        saved += 1
        print(f"ok {title} -> {out} ({len(plain)} chars)")
        time.sleep(2.5)
    print(f"saved {saved} pages")


if __name__ == "__main__":
    main()
