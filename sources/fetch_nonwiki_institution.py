"""从殆知阁 daizhigev20（GitHub）与 Kanripo 拉取非维基制度史料。

目标：扩大两汉侍中制度沿革语料，不限于维基文库。
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
VENDORS = ROOT / "vendors"
UA = "ShizhongDB/0.1 (academic research; local fetch)"

# 殆知阁 garychowcmu/daizhigev20 — 与侍中制度高度相关者
DAIZHIGE = [
    # (repo path, local book dir)
    ("史藏/政书/汉制攷.txt", "汉制考"),
    ("史藏/政书/汉官旧仪.txt", "汉官旧仪"),
    ("史藏/政书/通典.txt", "通典"),
    ("史藏/政书/文献通考.txt", "文献通考"),
    ("史藏/政书/续通典.txt", "续通典"),
    ("史藏/政书/西汉会要.txt", "西汉会要"),
    ("史藏/政书/东汉会要.txt", "东汉会要"),
    ("史藏/政书/补汉兵志.txt", "补汉兵志"),
    ("史藏/职官/唐六典.txt", "唐六典"),
    ("史藏/职官/钦定历代职官表.txt", "历代职官表"),
    ("史藏/职官/敦煌悬泉汉简.txt", "悬泉汉简"),
    ("史藏/职官/百官箴.txt", "百官箴"),
    ("子藏/类书/职官分纪.txt", "职官分纪"),
    ("子藏/类书/北堂书钞.txt", "北堂书钞"),
    ("子藏/类书/初学记.txt", "初学记"),
    ("子藏/类书/艺文类聚.txt", "艺文类聚"),
    ("子藏/类书/太平御览.txt", "太平御览"),
    ("子藏/类书/册府元龟.txt", "册府元龟"),
    ("子藏/类书/玉海.txt", "玉海"),
    ("史藏/诏令奏议/两汉诏令.txt", "两汉诏令"),
]

# Kanripo bkkbooks/KR2l0023 漢官六種
KANRIPO_HANGUAN = {
    "repo": "bkkbooks/KR2l0023",
    "branch": "master",
    "parts": [f"KR2l0023_{i:03d}.yaml" for i in range(1, 11)],
    "local_dir": "汉官六种",
}


def fetch(url: str, retries: int = 4) -> bytes:
    delay = 2.0
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < retries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            if e.code == 404:
                return b""
            raise
        except TimeoutError:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            raise
    return b""


def raw_github(repo: str, path: str, branch: str = "master") -> str:
    enc = urllib.parse.quote(path)
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{enc}"
    data = fetch(url)
    return data.decode("utf-8", errors="ignore")


def download_daizhige():
    base_repo = "garychowcmu/daizhigev20"
    report = []
    for rel, book in DAIZHIGE:
        out_dir = RAW / book
        out_dir.mkdir(parents=True, exist_ok=True)
        # 已有则跳过（若文件 >1k）
        fname = Path(rel).name
        out = out_dir / f"殆知阁_{fname}"
        if out.exists() and out.stat().st_size > 1000:
            print(f"cached {book}/{out.name} {out.stat().st_size}")
            report.append({"book": book, "path": str(out.relative_to(ROOT)), "status": "cached", "size": out.stat().st_size})
            continue
        print(f"fetch {rel} ...", flush=True)
        text = raw_github(base_repo, rel)
        if not text or len(text) < 50:
            print(f"  empty/fail {rel}")
            report.append({"book": book, "path": rel, "status": "fail", "size": 0})
            time.sleep(1.5)
            continue
        out.write_text(text, encoding="utf-8")
        n = text.count("侍中")
        print(f"  ok {out} chars={len(text)} 侍中={n}")
        report.append({"book": book, "path": str(out.relative_to(ROOT)), "status": "ok", "size": len(text), "shizhong": n})
        time.sleep(1.2)
    return report


def download_hanguan():
    out_dir = RAW / KANRIPO_HANGUAN["local_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    vend = VENDORS / "KR2l0023_漢官六種"
    vend.mkdir(parents=True, exist_ok=True)
    combined = []
    for part in KANRIPO_HANGUAN["parts"]:
        out = vend / part
        if out.exists() and out.stat().st_size > 100:
            text = out.read_text(encoding="utf-8", errors="ignore")
        else:
            print(f"fetch kanripo {part}", flush=True)
            text = raw_github(KANRIPO_HANGUAN["repo"], part)
            if not text:
                print("  fail", part)
                continue
            out.write_text(text, encoding="utf-8")
            time.sleep(1.2)
        combined.append(text)
    # yaml 正文多在 text: | 块或逐行；粗提中文
    body = "\n".join(combined)
    # 抽取 YAML 中的中文段
    chunks = re.findall(r"(?:text|line|content)\s*:\s*[|>]?\s*\n((?:\s+.+\n)+)", body)
    if not chunks:
        # 直接取含汉字的行
        lines = [ln.strip() for ln in body.splitlines() if re.search(r"[一-鿿]", ln)]
        plain = "\n".join(lines)
    else:
        plain = "\n".join(chunks)
    # 去掉 yaml 缩进与引号
    plain = re.sub(r"^\s+", "", plain, flags=re.M)
    plain = re.sub(r"^['\"]|['\"]$", "", plain, flags=re.M)
    out_txt = out_dir / "汉官六种_KR2l0023.txt"
    out_txt.write_text(plain, encoding="utf-8")
    n = plain.count("侍中")
    print(f"汉官六种 -> {out_txt} chars={len(plain)} 侍中={n}")
    return {"book": "汉官六种", "path": str(out_txt.relative_to(ROOT)), "status": "ok", "size": len(plain), "shizhong": n}


def main():
    report = []
    report.extend(download_daizhige())
    try:
        report.append(download_hanguan())
    except Exception as e:
        print("hanguan err", e)
        report.append({"book": "汉官六种", "status": "fail", "error": str(e)})
    out = ROOT / "data" / "candidates" / "nonwiki_fetch_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("report", out)
    for r in report:
        print(f"  {r.get('status')} {r.get('book')} 侍中={r.get('shizhong','-')} size={r.get('size')}")


if __name__ == "__main__":
    main()
