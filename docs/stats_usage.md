# 统计软件使用说明（两汉侍中数据库）

版本：2026-09-13  
库文件：`data/db/shizhong.db`  
导出：`data/exports/`（UTF-8-SIG，Excel / SPSS 可直接打开）

---

## 1. 数据包内容

| 文件 | 粒度 | 行数 | 用途 |
|------|------|------|------|
| `persons_wide.csv` | 一人一行 | 256 | 描述统计、交叉表、回归自变量 |
| `terms_long.csv` | 一人多行任职 | 518 | 任职次数、时期分布、事件史 |
| `relations_edges.csv` | 边一行 | 322 | 网络分析、图可视化 |
| `persons_attrs.csv` | 节点属性 | 256 | Gephi / Cytoscape / NetworkX |
| `stats_by_dynasty.csv` | 朝代汇总 | 10 | 快速核对 |
| `stats_by_reltype.csv` | 关系类型汇总 | 26 | 快速核对 |

SQLite 五表（可 SQL）：`person` · `source` · `shizhong_term` · `relation` · `candidate`

---

## 2. 字段字典（统计用）

### persons_wide.csv

| 字段 | 类型 | 说明 |
|------|------|------|
| id | 文本 | 主键 P#### |
| name | 文本 | 姓名 |
| style_name | 文本 | 字 |
| dynasty | 文本 | 原始朝代串（可含复合） |
| dynasty_primary | 文本 | **归一朝代**：西漢/東漢/新/更始/漢魏之際/魏/蜀漢/吳/晉/兩漢 |
| category | 文本 | 类属原文 |
| origin | 文本 | 籍贯 |
| birth / death | 文本 | 原文纪年（可含「阙」） |
| birth_year / death_year | 整数 | **公元**（负=公元前）；多数为 NULL |
| year_precision | 文本 | exact / approx / unknown |
| is_外戚 … is_勋贵 | 0/1 | 类属指示变量（由 category 启发式标注） |
| n_terms | 整数 | 任职记录条数 |
| n_sources | 整数 | 关联史料条数 |
| status | 文本 | 待审 / 草稿 / 已校 |

### terms_long.csv

| 字段 | 说明 |
|------|------|
| term_id, person_id, name | 定位 |
| start_ym, end_ym | 原文纪年串 |
| start_year, end_year | 公元（可空） |
| nature | 官名性质原文 |
| nature_primary | 加官 / 正職 / 近侍兼官 / 复合官 / 被表未行 / 其他 |
| evidence | 有明文 / 推断 / 阙疑 |
| book, juan, quote_head | 出处 |

### relations_edges.csv

| 字段 | 说明 |
|------|------|
| from_id, from_name, to_id, to_name | 两端；to_id 空=对方未建卡 |
| rel_type / rel_primary | 关系类型 |
| is_kinship / is_patron / is_conflict | 0/1 聚合 |

**注意**：`birth_year` 等大量 NULL 是史料实情，不是导入失败。统计时用 `year_precision` 过滤或只做有年子集。

---

## 3. Python（pandas）

```python
import sqlite3
import pandas as pd

con = sqlite3.connect("data/db/shizhong.db")
persons = pd.read_sql("SELECT * FROM person", con)
terms = pd.read_sql(
    "SELECT t.*, p.name, p.dynasty_primary FROM shizhong_term t "
    "JOIN person p ON p.id=t.person_id",
    con,
)
edges = pd.read_sql("SELECT * FROM relation", con)
con.close()

# 或直接读导出
persons = pd.read_csv("data/exports/persons_wide.csv", encoding="utf-8-sig")

# 朝代分布
persons.groupby("dynasty_primary").size().sort_values(ascending=False)

# 外戚比例
persons.groupby("dynasty_primary")["is_外戚"].mean()

# 有生卒年子集
dated = persons[persons["birth_year"].notna()]
```

网络（可选）：

```python
import networkx as nx
G = nx.from_pandas_edgelist(
    edges[edges["to_id"] != ""],
    "from_name", "to_name", edge_attr="rel_primary",
)
```

---

## 4. R（RSQLite / tidyverse）

```r
library(DBI)
library(RSQLite)
library(dplyr)
library(readr)

con <- dbConnect(RSQLite::SQLite(), "data/db/shizhong.db")
persons <- dbReadTable(con, "person")
terms   <- dbReadTable(con, "shizhong_term")
edges   <- dbReadTable(con, "relation")
dbDisconnect(con)

# 或
persons <- read_csv("data/exports/persons_wide.csv")

persons %>% count(dynasty_primary, sort = TRUE)
persons %>% group_by(dynasty_primary) %>% summarise(n = n(), 外戚 = sum(is_外戚))

# igraph
library(igraph)
g <- graph_from_data_frame(
  edges %>% filter(to_id != "") %>% select(from_name, to_name, rel_primary),
  directed = TRUE
)
```

---

## 5. Stata

```stata
* 推荐：先用 Excel/Python 导出 CSV，再
import delimited "data/exports/persons_wide.csv", encoding(utf8) clear
tabulate dynasty_primary
tabulate dynasty_primary is_外戚, row

import delimited "data/exports/terms_long.csv", encoding(utf8) clear
tabulate nature_primary
tabulate book

import delimited "data/exports/relations_edges.csv", encoding(utf8) clear
tabulate rel_primary
```

若本机 Stata 支持 SQLite/odbc，也可：

```stata
odbc load, exec("SELECT * FROM person") dsn("shizhong")
```

（需先配置 ODBC 数据源指向 `shizhong.db`。）

---

## 6. SPSS

1. 打开 `data/exports/persons_wide.csv`（UTF-8）  
2. 变量视图：将 `is_*` 设为名义 0/1；`birth_year` 设标度  
3. 频率 / 交叉表：`dynasty_primary` × `is_外戚`  
4. 边表可用「数据 → 个案排秩」或导出后用 NodeXL / Gephi  

---

## 7. Excel / WPS

直接双击打开 `data/exports/*.csv`（已带 BOM）。  
透视表：行=`dynasty_primary`，值=计数 `name` 或求和 `is_外戚`。

---

## 8. 网络可视化

### Gephi
1. `persons_attrs.csv` → 节点表（Nodes table），ID=`id` 或 `name`  
2. `relations_edges.csv` → 边表，Source=`from_name`，Target=`to_name`，Label=`rel_primary`  
3. 过滤 `to_id` 为空的边（对方未建卡）

### Cytoscape
同上，File → Import → Network from file

### 轻量 HTML
可后续用同一 SQLite 做本地查询页；导出边表也可喂 vis.js / ECharts graph。

---

## 9. 分析时的注意事项（方法论）

1. **名录未完成「已校」终审**：描述统计可做，写论文时应注明 status 过滤规则（例如仅 `待审+已校`）。  
2. **96 人仅 1 条引文**：频次会向「可考」偏置，属史料幸存偏差。  
3. **年份稀疏**（约 12 人有年）：时期分析请用 `dynasty_primary` 或 `terms_long` 中有 `start_year` 的子集。  
4. **is_* 为启发式**：来自 category 字符串，抽查后可手改 CSV 再分析。  
5. **郑玄**：`nature_primary=被表未行`，统计「曾任侍中」时应排除。  
6. **庾峻**：`dynasty_primary=晉`，两汉样本请过滤。  
7. **三国人物**：魏/蜀/吳/漢魏之際 单独成层，勿与两汉混为同一总体而不加控制。

---

## 10. 复现导出

```powershell
& $env:MIMO_PYTHON sources/stats_schema_upgrade.py   # 仅首次/改表时
& $env:MIMO_PYTHON sources/fix_term_nature.py
& $env:MIMO_PYTHON sources/export_stats_csv.py
& $env:MIMO_PYTHON sources/normalize_relations.py
```

库与 `data/exports/` 应始终从同一 `shizhong.db` 生成，避免 CSV 与库不一致。
