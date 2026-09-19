# 制度史语料：十通与非维基来源

更新：2026-09（GitHub/Kanripo 扩展轮）

## 关于 ctext 等平台

| 平台 | 能否用于本项目自动语料 |
|------|------------------------|
| **ctext.org** | **不能爬取**。项目 `CLAUDE.md` 明确：需机构订阅 JSON API；禁爬；有订阅再接 |
| 维基文库 | 可以（MediaWiki API） |
| Kanripo / bkkbooks（GitHub） | 可以（开放 YAML/文本） |
| 殆知阁 daizhigev20（GitHub） | 可以（开放 txt） |
| GitHub 上的 ctext 未授权镜像/爬虫仓 | **不用**（版权与规范风险） |
| 学术机构库（中华经典古籍库等） | 人工定点；不自动化 |

## 已入库渠道

| 渠道 | 用途 | 状态 |
|------|------|------|
| 维基文库 API | 正史、辑本、会要、通典/通考/唐六典卷次 | 已用 |
| Kanripo/bkkbooks | 漢官六種、通典/通考 YAML、職官分紀、歷代職官表、漢制考、漢官舊儀、東漢會要、冊府元龜選輯、**居延漢簡釋文合校** | 已用 |
| 殆知阁 daizhigev20 | 史藏政书/职官、子藏类书全文 | 已用（20+ 种） |
| GitHub 检索记录 | `data/candidates/github_corpus_search.json` | 已用 |

## Kanripo 关键 ID（与侍中相关）

| ID | 书 | 本地（抽样导入） |
|----|-----|------------------|
| KR2l0023 | 漢官六種 | `data/raw/汉官六种/` |
| KR2m0001 | 通典 | `data/raw/通典/bkkbooks_KR2m0001.txt`（部件抽样） |
| KR2m0007 | 東漢會要 | `data/raw/东汉会要/` |
| KR2m0008 | 漢制考 | `data/raw/汉制考/` |
| KR2m0020 | 漢官舊儀 | `data/raw/汉官旧仪/` |
| KR2m0009/0014/0015 | 文獻通考 / 續通考 / 皇朝通考 | 部分 YAML |
| KR2l0015 | 欽定歷代職官表 | `data/raw/历代职官表/` |
| KR3k0020 | 職官分紀 | `data/raw/职官分纪/`（约 392 处侍中） |
| KR5a0332 | **居延漢簡釋文合校** | `data/raw/居延汉简释文/`（本轮仅见 1 处「侍中谏大夫」类碎片） |
| KR6v0392 | 冊府元龜選輯 | `data/raw/册府元龟选辑/` |

## 殆知阁命中（摘要）

通典 833 · 文献通考 753 · 册府元龟 3140 · 太平御览 678 · 玉海 353 · 职官分纪 439 · 北堂书钞 174 · 历代职官表 165 等。详见 `nonwiki_fetch_report.json`。

## 命令

```powershell
& $env:MIMO_PYTHON sources/fetch_nonwiki_institution.py
& $env:MIMO_PYTHON sources/fetch_kanripo_extra.py
& $env:MIMO_PYTHON sources/fetch_shitong_sources.py
& $env:MIMO_PYTHON sources/build_institution_json.py
& $env:MIMO_PYTHON sources/export_institution_web.py
```

## GitHub 检索结论

- 有效开源几乎都落在 **Kanripo/bkkbooks** 与 **殆知阁** 两条线。
- 以「侍中」「十通职官」为题的独立专题库很少；GitHub 大量同名搜索命中政治杂文仓，**不可用**。
- 居延/尹湾/悬泉：Kanripo 仅有《居延汉简释文合校》抽样；尹湾、悬泉完整释文未见开放全本。

## 仍未占全

| 缺口 | 说明 |
|------|------|
| ctext 全文 | 禁爬；机构订阅 |
| 《通志》职官略正编 | 开放卷目不全 |
| 简牍全本 | 居延释文仅部分部件；尹湾/悬泉需另源 |
| 商业古籍库 | 人工定点 |

**判断**：ctext 不可用；GitHub 上合法、可用的电子化材料以 Kanripo + 殆知阁为主，本项目已尽量吸入。再扩优先级低于机构库与纸本简牍释文。
