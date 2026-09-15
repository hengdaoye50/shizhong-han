# 交接摘要（2026-09-13）

## 项目是什么
两汉侍中数据库：人物卡片 + 任职 + 关系 + 可检索本地库 + 静态 Web。

## 数据现状（可信）
- 语料：`data/raw/`（前四史维基+mirror、隸釋/續、東觀漢記、前後漢紀、全兩漢文、集古錄/金石錄）
- 候选句：`data/candidates/shizhong_candidates.csv`（约 1774）
- 人物卡：`data/cards/`（约 259 人；约 95 人已写全履历；制度卡 1 张已排除出时间轴）
- SQLite：`data/db/shizhong.db`
  - person 259 · source/term ~467 · relation 433
  - 郑玄=被表侍中未行；庾峻=晋附录
  - person 增列：`year_precision` / `term_start_year` / `term_end_year` / `term_label`
- 统计导出：`data/exports/`
- 统计说明：`docs/stats_usage.md`

## 前端现状
- 目录：`shizhongdata/` → 拷到 Hugo `static/shizhongdata/` 部署 `jinhuazhang.top/shizhongdata/`
- 本地预览：`& $env:MIMO_PYTHON -m http.server 8765 --directory shizhongdata`
- 首页：暗色关系图谱（转速已降）+ 名录检索
- 时间轴：`timeline.html` — **已重做，见下**

## 时间轴方法（2026-09-13 已修）
不再为「仅知朝代」者画整段假横条。三级精度：

| 精度 | 条件 | 画法 | 当前人数 |
|------|------|------|----------|
| era | 年号可定（建武二十年/嘉禾中） | 实心点 | 10 |
| reign | 帝号在位期（灵帝时/哀平间） | 半透明宽带 | 45 |
| exact | 生卒可考 | 淡寿命条（可选开关） | 51 |
| dynasty | 仅朝代 | **不画个人条**，进朝代聚合卡 | 152 |

- 脚本：`sources/build_timeline.py`（重写：帝号表 + 年号消歧 + 含侍中分句优先）
- 数据：`shizhongdata/data/timeline.json`（items=可定位 106，aggregates=11 组）
- 前端：`shizhongdata/assets/timeline.js` + `timeline.html`
- 横轴为**折线刻度**（汉末—三国拉宽）；魏/蜀/吴三条并行细带，避免同时代叠色
- 制度卡（佚名侍中）不进时间轴
- nature 占位「见原典…」只算朝代级，不再当线索

## 常用命令
```powershell
& $env:MIMO_PYTHON sources/query_db.py --stats
& $env:MIMO_PYTHON sources/export_web_json.py
& $env:MIMO_PYTHON sources/export_graph_json.py
& $env:MIMO_PYTHON sources/build_timeline.py
```

## 设计约束
- 主色 rgb(126,12,110) #7E0C6E
- 前端不展示「待审/草稿」
- 毛玻璃已弃用；首页暗色档案风；时间轴浅色纸本档案
- 新会话可继续：补更多人年号/生卒以提高上轴率、或关系边/导出/论文统计

## 新会话开场建议
读 `CLAUDE.md` + 本文件。时间轴已按精度分级，勿回退到「朝代窗口当任职期」。
若继续打磨：优先补 nature 中的年号/帝号线索（卡片校录），而非改可视化。
