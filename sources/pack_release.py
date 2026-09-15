"""打包发布用数据包：不含 raw/vendors/_archive/备份。"""
from __future__ import annotations

import shutil
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VER = "v1.0.0"
STAGE = ROOT / "_release_stage" / f"shizhong-han-{VER}"
ZIP = ROOT / "_release_stage" / f"shizhong-han-{VER}.zip"

if STAGE.parent.exists():
    shutil.rmtree(STAGE.parent)
STAGE.mkdir(parents=True)

INCLUDE = [
    ("README.md", "README.md"),
    ("docs", "docs"),
    ("data/cards", "data/cards"),
    ("data/db/shizhong.db", "data/db/shizhong.db"),
    ("data/exports", "data/exports"),
    ("data/bio", "data/bio"),
    ("data/candidates/shizhong_candidates.csv", "data/candidates/shizhong_candidates.csv"),
    ("shizhongdata", "shizhongdata"),
    ("sources", "sources"),
]

# 排除源码目录里的归档与 pyc
SKIP_PARTS = {"_archive", "__pycache__"}


def copy_tree(src: Path, dest: Path) -> None:
    if src.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        return
    for p in src.rglob("*"):
        if any(s in p.parts for s in SKIP_PARTS):
            continue
        if any(part.startswith("_backup") for part in p.parts):
            continue
        if p.suffix in {".pyc", ".db-journal", ".db-wal", ".db-shm"}:
            continue
        rel = p.relative_to(src)
        out = dest / rel
        if p.is_dir():
            out.mkdir(parents=True, exist_ok=True)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)


for src_rel, dest_rel in INCLUDE:
    src = ROOT / src_rel
    if not src.exists():
        print("skip missing", src_rel)
        continue
    copy_tree(src, STAGE / dest_rel)
    print("copied", src_rel)

# 发布说明
notes = STAGE / "RELEASE_NOTES.md"
notes.write_text(
    f"""# 两汉侍中数据库 {VER}

发布日期：{date.today().isoformat()}

## 内容

| 项 | 数量 |
|----|------|
| 人物卡片 | 258 |
| 任职条目 | 248 |
| 原典出处 | ~412 |
| 关系边 | 432 |
| 生平可考 | 147 |
| 时间轴可定位 | 164 |

## 目录

- `data/cards/` — 人物卡 Markdown（已统一简体，status=已校）
- `data/db/shizhong.db` — SQLite 主库
- `data/exports/` — 统计 CSV（UTF-8-SIG）
- `data/bio/bio.json` — 生平独立库
- `shizhongdata/` — 静态检索站（可直接部署）
- `docs/` — 字段与用法说明
- `sources/` — 导出与清洗脚本

## 在线

https://jinhuazhang.top/shizhongdata/

## 仓库

https://github.com/hengdaoye50/shizhong-han
""",
    encoding="utf-8",
)

with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(STAGE.rglob("*")):
        if p.is_file():
            z.write(p, p.relative_to(STAGE.parent).as_posix())

print("zip", ZIP, ZIP.stat().st_size)
print("files", sum(1 for p in STAGE.rglob("*") if p.is_file()))
