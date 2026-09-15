# 交接摘要（2026-09-15 巡检后）

## 项目是什么
两汉侍中数据库：人物卡片 + 任职 + 关系 + 生平（独立）+ SQLite + 静态 Web。

## Git 同步状态（重要）
- **本地文件已全部更新**（卡片/库/前端/README/CLAUDE/HANDOFF）
- **GitHub 远端仍停在 init/docs 旧提交**，约 300+ 变更未 commit
- 新增未跟踪：`about.html`、`bio.json`、`sources/hans.py`、清洗/富化脚本、`sources/_archive/`、`docs/audits/` 等
- 推送前请先人工 `git status` / `git diff` 审阅；**勿含** `preview_shots/`、`*.db.bak`、商业 PDF

## 规模（已校验一致）
- 卡片 **258** = 库 person **258** = Web **258**
- term 248 · source ~412 · relation 432 · person_bio 147 有实义
- 时间轴上轴 **164**（era31/reign82/exact51）· 仅朝代 **94**
- Web 筛选组：西汉60 东汉140 魏15 汉魏之际14 蜀汉11 吴8 新5 晋3 更始2
- 图谱节点 104（均在库内）

## 目录（整理后）
```
data/{raw,cards,candidates,bio,db,exports}
sources/          # 核心流水线，见 sources/README.md
sources/_archive/ # 一次性挖掘脚本
shizhongdata/     # 静态站（index/timeline/about）
vendors/          # 镜像 + books/ 参考 PDF
docs/audits/      # 巡检报告
preview_shots/    # 截图（建议不入 git）
```

## 核心命令
```powershell
& $env:MIMO_PYTHON sources/cleanup_cards_db.py
& $env:MIMO_PYTHON sources/enrich_year_clues.py
& $env:MIMO_PYTHON sources/fix_dup_quote_lines.py
& $env:MIMO_PYTHON sources/build_bio_store.py
& $env:MIMO_PYTHON sources/export_web_json.py
& $env:MIMO_PYTHON sources/build_timeline.py
& $env:MIMO_PYTHON sources/export_graph_json.py
```

## 巡检结论
- 卡片/库/Web/时间轴 ID 对齐，无制度卡、无重复 id
- relation 端点含帝号与非侍中人物（诸葛亮、董卓等）属设计如此
- 已修：晋字、两汉筛选简繁不匹配、朝代组归并、全站浅色主题

## 下一步
1. **审阅后 commit + push 到 GitHub**（当前最大缺口）
2. 人工审 `data/candidates/enrich_raw_hits.json`
3. 向 200+ 推生平
4. 部署 Hugo static
