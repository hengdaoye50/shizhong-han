# sources/ 脚本说明

按流水线阶段排列。一次性挖掘脚本在 `_archive/`，不参与日常重建。

## 核心重建（常用）

| 顺序 | 脚本 | 作用 |
|------|------|------|
| 1 | `cleanup_cards_db.py` | 删制度卡、繁→简、term/source 去重 |
| 2 | `enrich_year_clues.py` | 从卡片引文回填年号/帝号到 nature |
| 3 | `enrich_major_quotes.py` | 高价值人物从 raw 补「侍中」句（需审） |
| 4 | `fix_dup_quote_lines.py` | 卡片 YAML 重复 quote 行收尾 |
| 5 | `build_bio_store.py` | 抽「## 生平履历」→ `person_bio` + `bio.json` |
| 6 | `export_web_json.py` | 前端 `shizhong.json` |
| 7 | `build_timeline.py` | 时间轴 `timeline.json` + 回写 person 年代列 |
| 8 | `export_graph_json.py` | 关系图 `graph.json` |
| 9 | `export_stats_csv.py` | 统计宽表/长表 CSV |

```powershell
& $env:MIMO_PYTHON sources/cleanup_cards_db.py
& $env:MIMO_PYTHON sources/enrich_year_clues.py
& $env:MIMO_PYTHON sources/fix_dup_quote_lines.py
& $env:MIMO_PYTHON sources/build_bio_store.py
& $env:MIMO_PYTHON sources/export_web_json.py
& $env:MIMO_PYTHON sources/build_timeline.py
& $env:MIMO_PYTHON sources/export_graph_json.py
```

## 制度沿革与名录核对（2026-09）

| 脚本 | 作用 |
|------|------|
| `fetch_institution_sources.py` | 维基：独断/汉官旧仪/会要等 |
| `fetch_shitong_sources.py` | 维基：通典/文献通考/唐六典等 |
| `fetch_nonwiki_institution.py` | **殆知阁 + Kanripo 汉官六种**（类书/政书/职官分纪等） |
| `extract_institution.py` | 全语料「侍中」句抽取 + 初版名录对照 |
| `build_institution_json.py` | 按制度演变阶段编排（清洗+简体+去重+政书过滤） |
| `export_institution_web.py` | 导出前端 `shizhongdata/data/institution.json`（含拟补名单） |
| `audit_roster_institution.py` | 名录核对 CSV + `docs/roster_gap_report.md` |

```powershell
& $env:MIMO_PYTHON sources/fetch_institution_sources.py
& $env:MIMO_PYTHON sources/fetch_shitong_sources.py
& $env:MIMO_PYTHON sources/extract_institution.py
& $env:MIMO_PYTHON sources/build_institution_json.py
& $env:MIMO_PYTHON sources/audit_roster_institution.py
& $env:MIMO_PYTHON sources/export_institution_web.py
```

制度史料与十通边界见 `docs/shitong_sources.md`。  
页面：`shizhongdata/zhidu.html`。拟补人物须人工审定后建卡，勿自动入正式库。

## 采集与建库（低频）

- `wiki_fetch.py` / `import_mirror.py` / `import_kanripo.py` — 语料
- `extract_shizhong.py` / `extract_persons_full.py` — 候选句
- `build_full_cards.py` / `finalize_cards.py` / `clean_all_cards.py` — 卡片
- `init_db.py` / `query_db.py` — 库
- `build_relations_full.py` / `normalize_relations.py` — 关系边
- `hans.py` — 繁简与引文归一（被 cleanup/enrich 引用）

## 富化（按簇，可选）

- `enrich_full_career.py` / `enrich_core_cards.py` / `enrich_all_cards.py`
- `enrich_medium_careers.py` / `enrich_shuwei_careers.py`

## 归档 `_archive/`

语义挖掘、队列扫描、试点过滤等一次性脚本，保留可追溯，不再调用。
