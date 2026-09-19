"""定向补拉 Kanripo 中尚未用殆知阁覆盖的条目（少量 yaml 部件）。"""
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
VENDORS = ROOT / "vendors"
UA = "ShizhongDB/0.1 (academic research; local fetch)"

# (repo, book_dir, max_parts)
TARGETS = [
    ("bkkbooks/KR3k0020", "职官分纪", 30),  # 与殆知阁对校
    ("bkkbooks/KR2l0015", "历代职官表", 25),
    ("bkkbooks/KR2m0008", "汉制考", 15),
    ("bkkbooks/KR2m0020", "汉官旧仪", 10),
    ("bkkbooks/KR6v0392", "册府元龟选辑", 20),
    ("bkkbooks/KR2m0007", "东汉会要", 15),
]


def gh_contents(repo: str):
    url = f"https://api.github.com/repos/{repo}/contents/"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    delay = 3
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                time.sleep(delay)
                delay *= 2
                continue
            return []
        except Exception:
            time.sleep(2)
    return []


def raw_file(repo: str, name: str) -> str:
    url = f"https://raw.githubusercontent.com/{repo}/master/{urllib.parse.quote(name)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print("  fail", name, e)
        return ""


def main():
    report = []
    for repo, book, max_parts in TARGETS:
        out_dir = RAW / book
        out_dir.mkdir(parents=True, exist_ok=True)
        vend = VENDORS / repo.replace("/", "_")
        vend.mkdir(parents=True, exist_ok=True)
        items = gh_contents(repo)
        yamls = [
            it["name"]
            for it in items
            if it.get("name", "").endswith(".yaml") and "manifest" not in it["name"]
        ]
        yamls.sort()
        yamls = yamls[:max_parts]
        print(f"\n=== {repo} parts={len(yamls)} ===")
        chunks = []
        for name in yamls:
            out = vend / name
            if out.exists() and out.stat().st_size > 40:
                text = out.read_text(encoding="utf-8", errors="ignore")
            else:
                print(" fetch", name, flush=True)
                text = raw_file(repo, name)
                if text:
                    out.write_text(text, encoding="utf-8")
                time.sleep(1.1)
            if text:
                chunks.append(text)
        body = "\n".join(chunks)
        lines = [ln.strip() for ln in body.splitlines() if re.search(r"[一-鿿]", ln)]
        plain = "\n".join(lines) if lines else body
        plain = re.sub(r"^text:\s*", "", plain, flags=re.M)
        out_txt = out_dir / f"{repo.replace('/', '_')}.txt"
        out_txt.write_text(plain, encoding="utf-8")
        n = plain.count("侍中")
        print(f" saved {out_txt} chars={len(plain)} 侍中={n}")
        report.append({"repo": repo, "book": book, "path": str(out_txt.relative_to(ROOT)), "shizhong": n, "size": len(plain)})
    outp = ROOT / "data" / "candidates" / "kanripo_extra_report.json"
    outp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", outp)


if __name__ == "__main__":
    main()
