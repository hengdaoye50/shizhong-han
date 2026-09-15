# 两汉侍中数据库

两汉可考侍中的人物卡片、任职履历、关系边与本地检索库，并附静态 Web（关系图谱 / 名录 / 时间轴）。

## 仓库结构

```text
cards/                 人物卡片（Markdown，约 259 人）
exports/               统计用 CSV（wide / long / edges / attrs）
sources/               Python：拉取、抽取、清洗、导出
docs/                  字段字典、统计说明、考据表
web/                   静态站（可部署 jinhuazhang.top/shizhongdata/）
shizhong.db            SQLite 主库
HANDOFF.md             长会话交接说明
CLAUDE.md              项目规范
```

> 本 README 对应仓库根目录；若仓库内仍保留 `data/`、`sources/`、`shizhongdata/` 原路径，以实际目录名为准。

## 数据规模（约）

| 项 | 数量 |
|----|------|
| 人物 | 259 |
| 史料条 | ~467 |
| 关系边 | ~433 |
| 朝代 | 西漢 / 新 / 東漢 / 漢魏之際 / 魏 / 蜀漢 / 吳 / 晉（附录） |

## 使用

### SQLite

```python
import sqlite3
con = sqlite3.connect("shizhong.db")
# person / source / shizhong_term / relation / candidate
```

### 统计 CSV

见 `exports/` 或重新导出：

```powershell
& $env:MIMO_PYTHON sources/export_stats_csv.py
```

详见 `docs/stats_usage.md`（Python / R / Stata / SPSS / Gephi）。

### Web 本地预览

```powershell
& $env:MIMO_PYTHON -m http.server 8765 --directory shizhongdata
```

打开 `http://127.0.0.1:8765/`。

## 史料原则

- 每条事实尽量带出处（书名 + 卷 + 原文）
- 「有明文 / 推断 / 阙疑」分开
- 郑玄：袁隗表为侍中，**以父丧不行**，不计入任侍中
- 自动抽取结果须人工审后方可作正式名录

## 部署（个人站）

将 `shizhongdata/` 复制到 Hugo 站点 `static/shizhongdata/`，推送后即可访问  
`https://jinhuazhang.top/shizhongdata/`。
