# 两汉侍中 Web UI · 部署说明

本地路径：`shizhongdata/`  
目标 URL：`https://jinhuazhang.top/shizhongdata/`

## 结构

```text
shizhongdata/
├── index.html
├── assets/style.css
├── assets/app.js
└── data/shizhong.json    # 由 sources/export_web_json.py 生成
```

## 部署到 Hugo + Cloudflare

1. 将整个 `shizhongdata/` 复制到 Hugo 站点：

```text
<你的 hugo 仓库>/static/shizhongdata/
```

2. 提交并推送；Cloudflare Pages 自动构建后即可访问  
   `https://jinhuazhang.top/shizhongdata/`

3. 若站点有 `baseURL` 子路径配置，本目录为**静态资源**，一般无需改 Hugo 配置。

## 更新数据

```powershell
# 改库后
& $env:MIMO_PYTHON sources/export_stats_csv.py
& $env:MIMO_PYTHON sources/export_web_json.py
# 再拷贝 shizhongdata/ 到 Hugo static/
```

## 设计说明

- 主色 `#7E0C6E`（rgb 126,12,110），辅以紫粉渐变与磨砂玻璃面板
- 字体：标题宋体系（古典），正文系统无衬线
- 交互：朝代筛选、全文搜索、右侧毛玻璃详情抽屉
- 尊重 `prefers-reduced-motion`
