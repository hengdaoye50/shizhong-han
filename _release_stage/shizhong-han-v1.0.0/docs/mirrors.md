# 开源镜像仓库（clone 到 vendors/ 后使用，勿改上游）

## 已落地（2026-09-11）

| 仓库 | 范围 | 状态 |
|------|------|------|
| hunterhug/china-history | 仅前四史 sparse-checkout | 已在 `vendors/china-history` |
| 维基文库 API | 漢書127 + 後漢書131 + 史記130 + 三國志65 | `data/raw/{漢書,後漢書,史記,三國志}/` |
| mirror 转换文本 | 前四史 415 篇原文 | `data/raw/mirror/` |
| Kanripo 隸釋/隸續/東觀漢記/前後漢紀/集古錄/金石錄 | 七书 | `vendors/kanripo-*` → `data/raw/` |
| 维基 全漢文 63 + 全後漢文 106 | 严可均辑本 | `data/raw/全漢文/`、`data/raw/全後漢文/` |

候选 CSV：1774 条。详见 `docs/epigraphy.md`。

## 主用（骨架史料）

### hunterhug/china-history
- 链接: https://github.com/hunterhug/china-history
- 内容: 二十四史；本项目 **只取史记/汉书/后汉书/三国志**
- 转换: `python sources/import_mirror.py` → `data/raw/mirror/`

### Kanripo（漢籍リポジトリ）
- 隸釋: https://github.com/kanripo/KR2n0017
- 隸續: https://github.com/kanripo/KR2n0018
- 東觀漢記: https://github.com/kanripo/KR2d0002
- 导入: `python sources/import_kanripo.py`

## 补充（辑佚 / 职官 / 类书线索）

### garychowcmu/daizhigev20（殆知阁古代文献）
- 链接: https://github.com/garychowcmu/daizhigev20
- 规模: 约 2 GB+
- 建议: 需要汉官六种等再 sparse，不必全量

## 人物库（两汉覆盖弱，仅长尾参照）

### cbdb-project/cbdb_sqlite
- 链接: https://github.com/cbdb-project/cbdb_sqlite
- 建议: 可选；两汉侍中不以 CBDB 为骨架

## 克隆目标目录

```text
vendors/china-history/     # 已 sparse 前四史
```

文本质量：维基文库（含颜注/李贤注）优先作抽取底本；mirror 作对照与补缺。
