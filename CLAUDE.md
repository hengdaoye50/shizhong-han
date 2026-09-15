# 两汉侍中数据库

收集两汉侍中人物卡片、任职履历与人物关系，最终形成可检索的本地数据库与关系图谱。

**长会话交接请先读 `HANDOFF.md`。**

## 目录约定

```text
.
├── CLAUDE.md / HANDOFF.md / README.md
├── data/
│   ├── raw/            # 原文语料（不入 git）
│   ├── candidates/     # 自动抽取候选
│   ├── cards/          # 人物卡片 Markdown
│   ├── bio/            # 生平独立库导出 bio.json
│   ├── db/             # SQLite + 关系 CSV
│   └── exports/        # 统计宽表/长表
├── sources/            # 流水线脚本（见 sources/README.md）
│   └── _archive/       # 一次性挖掘脚本归档
├── shizhongdata/       # 静态站（部署拷贝此目录）
├── vendors/            # 外部镜像 + books/ 参考 PDF
├── docs/               # 字段字典、研究笔记、audits/
└── preview_shots/      # 本地截图（不入 git 亦可）
```

命名：人物卡片 `data/cards/<姓名>_<朝代>.md`；候选 CSV 用 UTF-8-SIG。

## 数据原则

1. 每一条事实必须带出处（书名 + 卷次 + 原文摘句）。
2. 「有明文」「推断」「阙疑」三态分开，推断不得写成确定。
3. 自动抽取只产出候选，不直接建正式卡片。
4. 外部镜像放 `vendors/`，只读；工程逻辑写在 `sources/`。
5. 生平只进 `person_bio` / `data/bio/bio.json`，不混入 term/source。
6. 显示字段用简体；制度卡不进名录与时间轴。

## 技术栈

- Python 3（优先 `$MIMO_PYTHON`），标准库为主；HTTP 用 `urllib` 或 `requests`。
- 存储：CSV 中间层 + SQLite 终库。
- 维基文库 API 拉卷；禁止爬 ctext。

## 常用命令

```powershell
# 维基文库拉卷（自动发现目录；注意限速，全书建议 sleep 3.5）
& $env:MIMO_PYTHON sources/wiki_fetch.py --discover 漢書
& $env:MIMO_PYTHON sources/wiki_fetch.py --book 漢書 --sleep 3.5
& $env:MIMO_PYTHON sources/wiki_fetch.py --book 後漢書 --only 19,26

# 开源镜像 HTML → 纯文本（前四史）
& $env:MIMO_PYTHON sources/import_mirror.py

# 从 raw 抽取「侍中」候选句
& $env:MIMO_PYTHON sources/extract_shizhong.py --input data/raw --output data/candidates/shizhong_candidates.csv
```

语料现状（2026-09-11）：前四史维基全量 + mirror；隸釋/隸續/東觀漢記/前後漢紀/集古錄/金石錄（Kanripo）；全漢文63+全後漢文106（维基）。候选约 1774 条。

## 验证

改动 `sources/` 后至少跑通一次试点：拉《漢書》卷 068 → 抽取 → 检查 candidates CSV 含霍光、金日磾、金安上等相关句。

## 全量建卡（现状 2026-09-15）

- 候选句：`data/candidates/shizhong_candidates.csv`
- 卡片：`data/cards/`（**258** 人）
- 库：`data/db/shizhong.db`（person 258 · term 248 · source ~412 · relation 432 · person_bio 258/147）
- 备份：`data/db/shizhong.db.bak-20260915`

```powershell
& $env:MIMO_PYTHON sources/query_db.py --stats
```

## 统计适配（2026-09-13）

- 库增列：`dynasty_primary`、`birth_year`、`is_*`、`nature_primary`、`rel_primary` 等
- 导出：`data/exports/*.csv`（wide / long / edges / attrs）
- 说明：`docs/stats_usage.md`（Python/R/Stata/SPSS/Gephi）
- 脚本：`stats_schema_upgrade.py` → `fix_term_nature.py` → `export_stats_csv.py`

## 关系边

- relation **432** 条；规范类型：与帝 / 同僚 / 父子兄弟 / 政敌 / 举主 / 府主 / 外戚姻亲 等
- 端点可为帝号、公主、非侍中历史人物（如诸葛亮、董卓）——属正常
- 查：`query_db.py --person 金日磾` / `--rel 举主`

## Web UI

- 目录：`shizhongdata/` → 拷到 Hugo `static/shizhongdata/` 部署 `jinhuazhang.top/shizhongdata/`
- 数据：`export_web_json.py` → `shizhong.json`；生平 `build_bio_store.py` → `bio.json`
- 详情：生平 / 任职 / 原典 / 关系；主色 `#7E0C6E`

## 时间轴

- 上轴 **164**（era 31 / reign 82 / exact 51）；仅朝代 **94**
- 折线刻度拉宽汉末—三国；魏蜀吴三条并行带

## 数据清洗（2026-09-15）

- `hans.py` 繁→简；`cleanup_cards_db.py` 删制度卡+去重；`enrich_year_clues.py` 回填年号
- 显示字段简体；制度卡不进名录/时间轴；生平独立存储

## 试点（已完成打样）

见 `docs/pilot.md`；详卡金日磾/金安上/窦宪等。

## 巡检

- 报告：`docs/audits/audit_2026-09-15.md`
- 脚本清单：`sources/README.md`
