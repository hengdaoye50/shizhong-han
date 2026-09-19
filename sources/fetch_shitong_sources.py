"""从维基文库拉取十通/唐六典等制度史文本，并筛出含「侍中」的卷。

输出:
  data/raw/通典/、文献通考/、唐六典/、通志/、冊府元龜/
  data/candidates/shitong_hits.json  命中摘要
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
OUT_HIT = ROOT / "data" / "candidates" / "shitong_hits.json"
API = "https://zh.wikisource.org/w/api.php"
UA = "ShizhongDB/0.1 (academic research; local fetch)"

# 目标：书名 -> (维基前缀/标题列表规则)
# 通典职官约在卷19–40；文献通考职官考约在卷47–67（四库本与数字卷并存）
TARGETS = {
    "通典": {
        "titles": [f"通典/卷{n:03d}" for n in range(19, 41)]
        + [f"通典/卷{n:03d}" for n in range(21, 23)],  # 门下/侍中常在此一带
        "priority_hint": ["侍中", "門下", "门下", "職官", "职官"],
    },
    "文献通考": {
        "titles": [
            "文獻通考/卷五十二",
            "文獻通考/卷五十三",
            "文獻通考/卷五十四",
            "文獻通考/卷五十五",
            "文獻通考/卷五十六",
            "文獻通考/卷五十七",
            "文獻通考/卷五十八",
            "文獻通考/卷五十九",
            "文獻通考/卷六十",
            "文獻通考/卷六十一",
            "文獻通考/卷六十二",
            "文獻通考/卷六十三",
            "文獻通考/卷六十四",
            "文獻通考/卷六十五",
            "文獻通考/卷六十六",
            "文獻通考/卷六十七",
            "文獻通考 (四庫全書本)/卷050",
            "文獻通考 (四庫全書本)/卷051",
            "文獻通考 (四庫全書本)/卷052",
            "文獻通考 (四庫全書本)/卷053",
            "文獻通考 (四庫全書本)/卷054",
            "文獻通考 (四庫全書本)/卷055",
            "文獻通考 (四庫全書本)/卷056",
            "文獻通考 (四庫全書本)/卷057",
            "文獻通考 (四庫全書本)/卷058",
            "文獻通考 (四庫全書本)/卷059",
            "文獻通考 (四庫全書本)/卷060",
            "文獻通考 (四庫全書本)/卷061",
            "文獻通考 (四庫全書本)/卷062",
            "文獻通考 (四庫全書本)/卷063",
            "文獻通考 (四庫全書本)/卷064",
            "文獻通考 (四庫全書本)/卷065",
            "文獻通考 (四庫全書本)/卷066",
            "文獻通考 (四庫全書本)/卷067",
        ],
        "priority_hint": ["侍中"],
    },
    "唐六典": {
        "titles": [f"唐六典/卷{n:02d}" for n in range(7, 13)],  # 门下/中书等
        "priority_hint": ["侍中", "門下", "门下"],
    },
    "通志": {
        "titles": [
            "通志/卷071",
            "通志/卷072",
            "通志/卷086",
            "通志/總序",
        ],
        "priority_hint": ["侍中"],
    },
    "冊府元龜": {
        "titles": [
            "冊府元龜 (四庫全書本)/卷0542",
            "冊府元龜 (四庫全書本)/卷0595",
            "冊府元龜 (四庫全書本)/卷0805",
            "冊府元龜 (四庫全書本)/卷0806",
        ],
        "priority_hint": ["侍中"],
    },
}


def api(params: dict, retries: int = 5) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    delay = 2.5
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < retries - 1:
                print(f"  {e.code}, sleep {delay:.1f}s", flush=True)
                time.sleep(delay)
                delay = min(delay * 2, 40)
                continue
            if e.code == 404:
                return {"missing": True}
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
    if d.get("missing") or "error" in d:
        return None
    return d.get("parse", {}).get("wikitext") or None


def to_plain(wikitext: str) -> str:
    t = wikitext
    t = re.sub(r"\{\{[^}]{0,400}\}\}", " ", t)
    t = re.sub(r"<ref[^>]*>.*?</ref>", " ", t, flags=re.S)
    t = re.sub(r"<ref[^/]*/>", " ", t)
    t = re.sub(r"\[\[[^\]|]+\|([^\]]+)\]\]", r"\1", t)
    t = re.sub(r"\[\[([^\]]+)\]\]", r"\1", t)
    t = re.sub(r"'''?", "", t)
    t = re.sub(r"={2,}", "\n", t)
    return t.strip() + "\n"


def slug(title: str) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", title)


def snippets(text: str, n: int = 8) -> list[str]:
    out = []
    flat = re.sub(r"\s+", "", text)
    for m in re.finditer(r"侍中", flat):
        a = max(0, m.start() - 30)
        b = min(len(flat), m.end() + 80)
        frag = flat[a:b]
        out.append(frag)
        if len(out) >= n:
            break
    return out


def main():
    hits = []
    for book, cfg in TARGETS.items():
        out_dir = RAW / book
        out_dir.mkdir(parents=True, exist_ok=True)
        titles = cfg["titles"]
        # 去重保序
        seen = set()
        uniq = []
        for t in titles:
            if t not in seen:
                seen.add(t)
                uniq.append(t)
        print(f"\n=== {book} ({len(uniq)} pages) ===")
        for title in uniq:
            out = out_dir / f"{slug(title)}.txt"
            if out.exists() and out.stat().st_size > 300:
                text = out.read_text(encoding="utf-8", errors="ignore")
                status = "cached"
            else:
                try:
                    wt = fetch_page(title)
                except Exception as e:
                    print(f"FAIL {title}: {e}")
                    time.sleep(3)
                    continue
                if not wt:
                    print(f"missing {title}")
                    time.sleep(1.5)
                    continue
                text = to_plain(wt)
                out.write_text(text, encoding="utf-8")
                status = "fetched"
                time.sleep(2.2)
            n_sz = text.count("侍中")
            mark = "*" if n_sz else " "
            print(f"{mark} {status:7s} {title:40s} 侍中={n_sz} chars={len(text)}")
            if n_sz:
                hits.append(
                    {
                        "book": book,
                        "title": title,
                        "path": str(out.relative_to(ROOT)).replace("\\", "/"),
                        "shizhong_count": n_sz,
                        "snippets": snippets(text, 6),
                    }
                )
    OUT_HIT.parent.mkdir(parents=True, exist_ok=True)
    OUT_HIT.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nhit volumes: {len(hits)} -> {OUT_HIT}")
    for h in hits:
        print(f"- {h['book']} {h['title']} n={h['shizhong_count']}")
        if h["snippets"]:
            print("   ", h["snippets"][0][:100])


if __name__ == "__main__":
    main()
