# 两汉侍中数据库

收集两汉侍中人物卡片、任职履历与人物关系，最终形成可检索的本地数据库与关系图谱。

**长会话交接请先读 `HANDOFF.md`。**

## 目录约定

```text
.
├── CLAUDE.md           # 本文件，项目规范
├── data/
│   ├── raw/            # 原文语料（维基文库拉取 / 开源镜像整理后的纯文本）
│   ├── candidates/     # 自动抽取的候选句（CSV），待人工校录
│   ├── cards/          # 人工校录后的人物卡片（Markdown，一人一文件）
│   └── db/             # SQLite 库与导出表
├── sources/            # 采集与抽取脚本（Python，仅标准库 + 可选 requests）
├── vendors/            # 外部开源镜像（git clone 下来，不改动上游）
└── docs/               # 字段字典、史料清单、研究笔记
```

命名：人物卡片 `data/cards/<姓名>_<朝代>.md`；候选 CSV 用 UTF-8-SIG（Excel 可开）。

## 数据原则

1. 每一条事实必须带出处（书名 + 卷次 + 原文摘句）。
2. 「有明文」「推断」「阙疑」三态分开，推断不得写成确定。
3. 自动抽取只产出候选，不直接建正式卡片。
4. 外部镜像放 `vendors/`，只读；工程逻辑写在 `sources/`。

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

## 全量建卡（进行中）

- 候选句：`data/candidates/shizhong_candidates.csv`（1774）
- 人名索引：`data/candidates/persons_index.csv`（约 203 人，自动抽取）
- 证据表：`data/candidates/persons_evidence.csv`
- 卡片：`data/cards/`（约 214，含试点详卡 + 全量骨架 `status: 草稿`）
- 库：`data/db/shizhong.db`

```powershell
& $env:MIMO_PYTHON sources/extract_persons_full.py
& $env:MIMO_PYTHON sources/build_full_cards.py
& $env:MIMO_PYTHON sources/query_db.py --stats
```

## 统计适配（2026-09-13）

- 库增列：`dynasty_primary`、`birth_year`、`is_*`、`nature_primary`、`rel_primary` 等
- 导出：`data/exports/*.csv`（wide / long / edges / attrs）
- 说明：`docs/stats_usage.md`（Python/R/Stata/SPSS/Gephi）
- 脚本：`stats_schema_upgrade.py` → `fix_term_nature.py` → `export_stats_csv.py`

## 关系边（2026-09-13）

- 全库 **259** 人 · 关系 **433** 边 · source 467（2026-09-13）。约 86+ 人已写全履历；注疏基本清除（余 2）。
- 生成：`sources/build_relations_full.py` → `sources/normalize_relations.py`
- 表：`data/db/relations_full.csv`；库 `relation` 约 **322** 条
- 规范类型：与帝 / 同僚 / 父子兄弟 / 政敌 / 举主 / 府主 / 外戚姻亲 / 与大将军 等
- 世系已补对称边；`to_id` 双端可连约 100 条
- 查：`query_db.py --person 金日磾` / `--rel 举主`

## Web UI（2026-09-13）

- 目录：`shizhongdata/` → 拷到 Hugo `static/shizhongdata/` 部署 `jinhuazhang.top/shizhongdata/`
- 数据：`sources/export_web_json.py` → `shizhongdata/data/shizhong.json`
- 主色 `#7E0C6E`，磨砂玻璃抽屉，搜索+朝代筛选
- 说明：`shizhongdata/README.md`

## 时间轴（2026-09-13 重做）

- 脚本：`sources/build_timeline.py` → `shizhongdata/data/timeline.json`
- 精度分级：era（年号点）/ reign（帝号宽带）/ exact（生卒淡条）/ dynasty（不画个人条，只聚合）
- 当前约：上轴 106 人，仅朝代 152 人；制度卡不进时间轴
- 页面：`shizhongdata/timeline.html`；勿再把朝代窗口当任职期

## 卡片质量（2026-09-13）

- 清洗：`sources/clean_all_cards.py`（去注疏、去重、去碎片引文）
- 全履历：`sources/enrich_full_career.py`（卫青/霍光/金氏/窦宪/张衡等 14 人）
- 任职 nature 不再重复堆「有明文」；引文不再含「（注：…）」

- 全履历：14+49+23 ≈ **86 人**已写侍中以外官职与事件
- 引文去重去注；剩余短引文多为仅一见的次要人物

## 试点（已完成打样）

见 `docs/pilot.md`；详卡金日磾/金安上/窦宪等。
