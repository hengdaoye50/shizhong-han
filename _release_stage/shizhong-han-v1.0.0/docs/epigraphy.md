# 碑刻与辑佚材料：获取现状

更新：2026-09-11

## 已自动入库（Kanripo / GitHub，CC BY-SA）

| 材料 | Kanripo ID | GitHub | 本地路径 | 卷数 |
|------|------------|--------|----------|------|
| 《隸釋》洪适 | KR2n0017 | [kanripo/KR2n0017](https://github.com/kanripo/KR2n0017) | `data/raw/隸釋/` | 29 |
| 《隸續》洪适 | KR2n0018 | [kanripo/KR2n0018](https://github.com/kanripo/KR2n0018) | `data/raw/隸續/` | 22（卷九、十原阙） |
| 《東觀漢記》辑本 | KR2d0002 | [kanripo/KR2d0002](https://github.com/kanripo/KR2d0002) | `data/raw/東觀漢記/` | 25 |

导入命令：`python sources/import_kanripo.py`

抽取结果：隸釋 15 条、隸續 7 条、東觀漢記 22 条含「侍中」句（见 candidates CSV）。

## 便利获取方式总表

| 资源 | 可否批量/API | 说明 |
|------|--------------|------|
| Kanripo（汉籍） | **可以** GitHub clone | 四库/四部叢刊电子文本，本项目主力 |
| 维基文库 | **可以** MediaWiki API | 前四史已全量；《隸釋》卷页不全故改走 Kanripo |
| hunterhug/china-history | **可以** git sparse | 前四史章节 HTML，已用 |
| 殆知阁 daizhigev20 | 可以但 2GB+ | 暂未拉；需要再 sparse |
| 汉典石刻 / 国学网 | **无开放 API** | 网页检索，自动化不划算，作人工核验 |
| 《汉魏南北朝墓志汇编》 | **无结构化开放数据** | 纸书/影印；商业库多为机构订阅 |
| 书格 shuge.org | 单册 PDF | 影印本可下，不能做全文检索语料 |
| ctext | 需机构订阅 JSON API | 禁爬；有订阅再接 |
| CBDB SQLite | 可以 GitHub | 两汉覆盖弱，仅长尾 |

## 对侍中研究的实际含义

两汉侍中**碑刻生平**的学术主流入口就是《隸釋》《隸續》+ 传世正史，不是现代在线碑刻库。我们已把可程序化拿到的部分拿下。

墓志汇编、汉典等：
1. 作为**定点核验**（某人某碑）时人工打开网页；
2. 不作为第一期建库依赖；
3. 若学校有「中华经典古籍库」等订阅，再按需补对校。

## 后续可选 Kanripo 目标（尚未 clone）

- `KR2k0058` 水經注（碑刻线索多）
- `KR2a0007` 前漢書 / `KR2a0009` 後漢書（与维基对校）
- 四庫史部金石类相邻编号（需按目录再筛）
