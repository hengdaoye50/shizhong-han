# 两汉侍中数据库

**Shizhong of the Han — A Prosopographical Database of Han-Dynasty Palace Attendants**

本仓库整理两汉（含新莽、更始及汉魏之际可考者）**侍中**人物的卡片、任职信息、人物关系与原典出处，并提供 SQLite 主库、统计导出表与可本地部署的静态检索站。

> 侍中在西汉多为加官、出入禁中的近臣；东汉渐成少府属官、比二千石，「无员」而亲近顾问。本库以「可考曾任侍中」为收录轴心，服务制度史、政治史与人物网络研究。

---

## 1. 收录范围

### 1.1 时间与政权

| 范围 | 说明 |
|------|------|
| **主体** | 西汉、新、更始、东汉 |
| **附录** | 汉魏之际、魏、蜀汉、吴（凡史载曾任侍中者，用 `dynasty` 字段区分） |
| **例外** | 魏晋之交个别连带人物（如庾峻）标为晋，不计入两汉正编 |

### 1.2 收录对象

- 史传、碑刻、诏令中**明文可考**曾任侍中（含侍中仆射、侍中驸马都尉、侍中祭酒等复合官）者。
- **被表荐为侍中而未就任**者单独标注（如郑玄：袁隗表为侍中，以父丧不行），**不计入「曾任侍中」**。
- 制度性、无名可考的「遣侍中某」等，进考据表，不建人物卡。

### 1.3 当前规模（2026-09-15）

| 项 | 数量 |
|----|------|
| 人物卡片 | **258** |
| 任职条目 | **248** |
| 原典出处条 | **~412** |
| 关系边 | **432** |
| 生平可考（独立库） | **147** |
| 时间轴可定位 | **164** |

朝代分布（筛选归并组，约）：东汉 140 · 西汉 60 · 魏 15 · 汉魏之际 14 · 蜀汉 11 · 吴 8 · 新 5 · 晋 3 · 更始 2。  
复合标签（如 `西汉_新`、`魏_晋`）在 Web 导出中归并到上列组，完整标签见 `dynasty_full` / 卡片 `dynasty` 字段。

### 1.4 明确不在本库范围

- 完整三国侍中名录（仅收入与两汉制度衔接或史有明文者）
- 无侍中任职证据、仅「近侍」「郎官」等
- 纯制度条文（已入制度考据卡，不单独立人）

---

## 2. 资料来源

### 2.1 主干正史（维基文库校勘本 + 章节镜像）

| 书 | 用途 |
|----|------|
| 《史记》 | 西汉早期近臣、外戚 |
| 《汉书》 | 西汉–新莽；百官公卿表、列传 |
| 《后汉书》 | 东汉主干；百官志、皇后纪、类传、列传 |
| 《三国志》 | 汉魏之际与三国侍中 |

### 2.2 编年与辑佚

- 《前汉纪》《后汉纪》（荀悦、袁宏）
- 《东观汉记》辑本
- 《全汉文》《全后汉文》（严可均辑，诏令、奏议）

### 2.3 金石

- 《隶释》《隶续》（洪适）
- 《集古录》《金石录》（欧阳修、赵明诚）

### 2.4 未入库说明

- 《汉魏南北朝墓志汇编》（赵超）：商业出版物，**不随仓库分发**；OCR 仅作页级线索，引用须核原书。
- ctext 等商业/订阅库：不爬取；研究引用请以纸本或机构订阅为准。

### 2.5 拉取脚本

语料可用仓库脚本重建（需网络，遵守源站条款）：

```powershell
# 维基文库按卷拉取
& $env:MIMO_PYTHON sources/wiki_fetch.py --book 漢書 --sleep 3.5
# 镜像 HTML → 纯文本
& $env:MIMO_PYTHON sources/import_mirror.py
# Kanripo（隶释等）导入
& $env:MIMO_PYTHON sources/import_kanripo.py
```

`data/raw/` 与 `vendors/` 默认不入 git。

---

## 3. 仓库结构

```text
README.md                 本说明
CLAUDE.md                 工程与数据规范
HANDOFF.md                长任务交接摘要
docs/
  stats_usage.md          各统计软件详细用法
  card_template.md        卡片字段模板
  pilot.md                试点与审录流程
  anonymous_kaoju.md      佚名/待考考据表说明
  epigraphy.md / mirrors.md
data/
  cards/                  人物卡 Markdown（一人一文件）
  db/shizhong.db          SQLite 主库
  exports/                统计导出 CSV
  candidates/             候选句、人名录、审读表
sources/                  Python：抽取、清洗、导出、查询
shizhongdata/             静态站（可部署个人域名子路径）
```

---

## 4. 数据模型（SQLite）

库文件：`data/db/shizhong.db`

| 表 | 粒度 | 主要字段 |
|----|------|----------|
| **person** | 一人一行 | id, name, style_name, dynasty, dynasty_primary, category, origin, birth/death, is_外戚/士人/降人/佞幸/宦官/勋贵, n_terms, n_sources |
| **shizhong_term** | 一人多行任职 | person_id, start/end_ym, start/end_year, nature, evidence |
| **source** | 出处条 | book, juan, quote, path |
| **relation** | 边 | from/to_id, from/to_name, rel_primary, is_kinship/patron/conflict |
| **candidate** | 候选句 | sentence, book, juan, status, person |

**证据三态**：`有明文` / `推断` / `阙疑`。  
**卡片 status**：本发布版统一为 `已校`；历史工作流字段不再对外展示。

---

## 5. 如何调取数据

### 5.1 直接用 SQLite（推荐）

```python
import sqlite3
import pandas as pd

con = sqlite3.connect("data/db/shizhong.db")

persons = pd.read_sql("SELECT * FROM person", con)
terms = pd.read_sql(
    """
    SELECT t.*, p.name, p.dynasty_primary
    FROM shizhong_term t
    JOIN person p ON p.id = t.person_id
    """,
    con,
)
edges = pd.read_sql("SELECT * FROM relation", con)
quotes = pd.read_sql("SELECT * FROM source", con)

# 例：东汉外戚侍中
df = persons[(persons.dynasty_primary == "東漢") & (persons.is_外戚 == 1)]

# 例：仅用已校
# persons = persons[persons.status == "已校"]

con.close()
```

### 5.2 使用现成导出 CSV

路径：`data/exports/`（UTF-8-SIG，Excel / SPSS 可直接打开）

| 文件 | 说明 |
|------|------|
| `persons_wide.csv` | 一人一行（宽表，适合描述统计与回归） |
| `terms_long.csv` | 任职长表（一人多行） |
| `relations_edges.csv` | 关系边表 |
| `persons_attrs.csv` | 节点属性（网络软件） |
| `stats_by_dynasty.csv` / `stats_by_reltype.csv` | 汇总核对 |

重新生成：

```powershell
& $env:MIMO_PYTHON sources/export_stats_csv.py
& $env:MIMO_PYTHON sources/export_web_json.py
```

### 5.3 命令行速查

```powershell
& $env:MIMO_PYTHON sources/query_db.py --stats
& $env:MIMO_PYTHON sources/query_db.py --person 金安上
& $env:MIMO_PYTHON sources/query_db.py --rel 举主
```

### 5.4 本地 Web 预览

```powershell
& $env:MIMO_PYTHON -m http.server 8765 --directory shizhongdata
# http://127.0.0.1:8765/            图谱 + 名录
# http://127.0.0.1:8765/timeline.html 时间轴
# http://127.0.0.1:8765/about.html   方法说明
```

静态站三页共用浅色纸本主题与顶栏导航；方法说明页与本 README 对应。  
部署：将 `shizhongdata/` 放入 Hugo `static/`。  
仓库：[hengdaoye50/shizhong-han](https://github.com/hengdaoye50/shizhong-han)

---

## 6. 导入主流统计软件

完整字段字典、示例与方法论注意见 **`docs/stats_usage.md`**。摘要如下。

### 6.1 Python（pandas）

```python
import sqlite3, pandas as pd
con = sqlite3.connect("data/db/shizhong.db")
persons = pd.read_sql("SELECT * FROM person", con)
con.close()

persons.groupby("dynasty_primary").size().sort_values(ascending=False)
persons.groupby("dynasty_primary")["is_外戚"].mean()

# 网络
import networkx as nx
edges = pd.read_csv("data/exports/relations_edges.csv", encoding="utf-8-sig")
edges = edges[edges["to_id"].fillna("") != ""]
G = nx.from_pandas_edgelist(edges, "from_name", "to_name", edge_attr="rel_primary")
```

### 6.2 R（RSQLite / tidyverse）

```r
library(DBI); library(RSQLite); library(dplyr); library(readr)
con <- dbConnect(RSQLite::SQLite(), "data/db/shizhong.db")
persons <- dbReadTable(con, "person")
dbDisconnect(con)

# 或
persons <- read_csv("data/exports/persons_wide.csv")
persons %>% count(dynasty_primary, sort = TRUE)
```

### 6.3 Stata

```stata
import delimited "data/exports/persons_wide.csv", encoding(utf8) clear
tabulate dynasty_primary
tabulate dynasty_primary is_外戚, row

import delimited "data/exports/terms_long.csv", encoding(utf8) clear
tabulate nature_primary
```

### 6.4 SPSS

1. 打开 `persons_wide.csv`（UTF-8）  
2. 将 `is_*` 设为名义 0/1；`birth_year` 设为标度  
3. 频率 / 交叉表：`dynasty_primary` × `is_外戚`

### 6.5 Excel / WPS

直接打开 `data/exports/*.csv`（已带 BOM）。透视表：行 = 朝代，值 = 计数姓名或求和 `is_外戚`。

### 6.6 Gephi / Cytoscape

| 角色 | 文件 | 列 |
|------|------|-----|
| 节点 | `persons_attrs.csv` | id 或 name |
| 边 | `relations_edges.csv` | from_name → to_name，Label = rel_primary |

建议过滤 `to_id` 为空的边（对方未建卡）。

---

## 7. 方法论与使用注意

1. **名录为「可考」下限**，非绝对全集；未解析句与碑刻残泐仍可能增补。  
2. **仅 1 条引文**的次要人物较多，属史料幸存偏差，写论文时应说明。  
3. **`is_*` 类属**由 category 启发式生成，建议抽查后手改再分析。  
4. **年份稀疏**：多数仅有朝代；时间分析请用有 `start_year`/`birth_year` 的子集，或仅作朝代分布。  
5. **郑玄**等「被表未行」请在统计「曾任侍中」时排除。  
6. **引文已尽量去注疏**；正式引用请回核点校本。

---

## 8. 许可与引用

- 人物卡、关系边与脚本：本项目自有整理成果。  
- 原典正文：公有领域古籍；维基文库等整理本请遵守其协议并核对纸本。  
- 若用于论文或报告，建议注明：数据版本、access 日期，以及「据两汉正史与金石辑本整理之侍中名录（本仓库）」。

---

## 9. 开发与维护

```powershell
# 常用链路
& $env:MIMO_PYTHON sources/query_db.py --stats
& $env:MIMO_PYTHON sources/clean_all_cards.py
& $env:MIMO_PYTHON sources/reassign_ids.py
& $env:MIMO_PYTHON sources/normalize_relations.py
& $env:MIMO_PYTHON sources/export_stats_csv.py
```

更细的工程约定见 `CLAUDE.md`；长任务上下文见 `HANDOFF.md`。
