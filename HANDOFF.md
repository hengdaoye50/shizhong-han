# 交接摘要（制度沿革提交轮）

## 项目是什么
两汉侍中数据库：人物卡片 + 任职 + 关系 + 生平（独立）+ SQLite + 静态 Web。

## Git 同步状态（重要）
- **main 已与 `origin/main` 对齐**（先前 v1.0.0 / 清洗 / README 等已推送，`2b1ef0e`）
- **本轮未推**：制度沿革 + 名录核对（`zhidu.html`、制度流水线、拟补草稿等）
- 已忽略：`data/raw/`、`vendors/`、`preview_shots/`、`data/db/*.bak*`、`*.pdf`
- 推送前仍应用 `git status` / `git diff` 审阅；**勿含**备份库与商业 PDF

## 规模（nature 回填后）
- 卡片 **268** · person_bio 有实义 **227** · source ~478 · relation 464
- 时间轴：plotted **177**（era 35 / reign 91 / exact 51）· 仅朝代聚合 91
- nature 回填脚本：`sources/apply_nature_clues.py`（只写原典可核验表述；纠郭昌/李尤/郑均/王歙误项）
- 待 push：enrich + 生平扩写 + nature/时间轴（本地多提交，网络曾失败）

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
# 制度沿革页 + 名录核对
& $env:MIMO_PYTHON sources/fetch_institution_sources.py
& $env:MIMO_PYTHON sources/extract_institution.py
& $env:MIMO_PYTHON sources/build_institution_json.py
& $env:MIMO_PYTHON sources/audit_roster_institution.py
& $env:MIMO_PYTHON sources/export_institution_web.py
```

## 制度沿革（2026-09 新增）

- 页面：`shizhongdata/zhidu.html`（与图谱/时间轴/方法说明并列）
- 数据：`shizhongdata/data/institution.json`（9 阶段 + 拟补名单）
- 名录核对报告：`docs/roster_gap_report.md`
- 拟补草稿卡：`data/candidates/draft_cards/`（辛毗、张辟强、孔安国、卓茂、卫觊、孙资、丁冲、金建等）— **未入库**
- 新拉制度语料：`data/raw/{獨斷,漢官舊儀,西漢會要,東漢會要}/`

## 巡检结论
- 卡片/库/Web/时间轴 ID 对齐，无制度卡、无重复 id
- relation 端点含帝号与非侍中人物（诸葛亮、董卓等）属设计如此
- 已修：晋字、两汉筛选简繁不匹配、朝代组归并、全站浅色主题

## 下一步
1. ~~push 制度沿革~~ `0dad4b2` · ~~拟补~~ `57254c6`
2. ~~enrich_raw_hits 审读~~ · ~~生平扩写至 227~~ — enrich `47cbf1f` **仅本地，待 push**（GitHub 代理曾失败）
3. 本地 push 重试或用户终端 `git push origin main`
4. 部署 Hugo static（含 zhidu 页）— 可与 push 并行
5. 可选：向剩余弱生平再挖 raw 本传（仍须带出处）
3. 人工审 `data/candidates/enrich_raw_hits.json`
4. 向 200+ 推生平
5. 部署 Hugo static（含 zhidu 页）
