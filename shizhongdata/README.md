# 两汉侍中 Web UI · 部署说明

本地路径：`shizhongdata/`  
目标 URL：`https://jinhuazhang.top/shizhongdata/`  
代码仓库：https://github.com/hengdaoye50/shizhong-han

## 结构

```text
shizhongdata/
├── index.html          # 图谱 + 名录
├── timeline.html       # 时间轴
├── about.html          # 方法说明（与 README 对应）
├── assets/
│   ├── style.css
│   ├── about.css
│   ├── app.js / graph.js / timeline.js
└── data/
    ├── shizhong.json   # export_web_json.py
    ├── timeline.json   # build_timeline.py
    ├── graph.json      # export_graph_json.py
    └── bio.json        # build_bio_store.py
```

三页共用顶栏导航（图谱名录 / 时间轴 / 方法说明 + GitHub）。

## 部署到 Hugo + Cloudflare

1. 将整个 `shizhongdata/` 复制到 Hugo 站点 `static/shizhongdata/`
2. 提交推送；Cloudflare Pages 构建后即可访问  
   `https://jinhuazhang.top/shizhongdata/`

## 更新数据

```powershell
& $env:MIMO_PYTHON sources/export_web_json.py
& $env:MIMO_PYTHON sources/build_timeline.py
& $env:MIMO_PYTHON sources/build_bio_store.py
& $env:MIMO_PYTHON sources/export_graph_json.py
# 再拷贝 shizhongdata/ 到 Hugo static/
```

## 设计说明

- 主色 `#7E0C6E`；全站统一**浅色纸本档案**（与时间轴一致）
- 背景：`#faf6f9 → #f3ebf3 → #ebe0eb`；卡片白底
- 详情：生平（独立库）/ 任职 / 原典 / 关系
- 尊重 `prefers-reduced-motion`
