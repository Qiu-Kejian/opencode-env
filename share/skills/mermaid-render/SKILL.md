---
name: mermaid-render
description: 把 mermaid 图渲染为 PNG/SVG（复用 Playwright Chromium，零额外浏览器下载），并可嵌入 officecli 文档（PPT/Word）。Use when 用户要画/渲染 mermaid、架构图、流程图、时序图，或要把图嵌入 PPT/Word/Markdown。触发词：mermaid、画架构图、渲染图、导出图表、嵌入图。
---

# mermaid-render · mermaid 渲染（本地零依赖浏览器）

> 用途：把 `.mmd` 渲染成 PNG/SVG。默认复用本机 Playwright Chromium（P1-10 已装），**不额外下载浏览器**；优先用本地 `.opencode/tools/mermaid/node_modules` 里的 mermaid-cli，缺失才回退 npx。

## 用法

```powershell
node .opencode/tools/mermaid-render.mjs <input.mmd> [-o out.png] [--svg] [--scale 3] [--bg white|transparent] [--preset ocean|none]
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `-o, --out` | 与输入同名 `.png`（`--svg` 时 `.svg`） | 输出路径；目录自动创建 |
| `--svg` | 关 | 输出矢量 SVG（PNG 便于嵌 PPT，SVG 便于二次编辑） |
| `--scale` | `3` | 缩放倍数（PPT 用建议 3） |
| `--bg` | `white` | `transparent` 用于叠深色底 |
| `--preset` | `ocean` | `ocean` = 微软雅黑 + Ocean 配色（见下）；`none` = 原样渲染。**文件已含 `%%{init}%%` 时不覆盖** |

脚本结束会打印输出路径与尺寸（含高/宽比，便于判断 16:9 适配）。

## 主题预设（ocean）

`fontFamily: Microsoft YaHei`；`primaryColor #F3F7FA` / `primaryTextColor #2B3A4E` / `primaryBorderColor #065A82` / `lineColor #1C7293`。
自定义配色：在 `.mmd` 顶部写 `%%{init: {"themeVariables": {...}}}%%`（脚本检测到即不注入）。

## 嵌入 officecli（PPT/Word）

```powershell
officecli add <file.pptx> "/slide[N]" --type picture `
  --prop src="C:\path\arch.png" --prop x=2.2cm --prop y=3.2cm `
  --prop width=11.61cm --prop height=14.4cm --prop alt="组织架构图：…"
```

- **必须给 `alt`**；嵌完跑 `officecli query <file> 'picture:no-alt'` 应返回 0。
- 比例换算：`宽 = 高 ÷ (高/宽比)`；16:9 页面内容区约 30.87×15.4cm。

## 坑位清单

1. **Playwright 升级换目录**：脚本自动探测 `%LOCALAPPDATA%\ms-playwright\chromium-*\chrome-win64\chrome.exe`（含 headless-shell 回退）；找不到时提示 `npx playwright install chromium`。
2. **别让 puppeteer 下载浏览器**：脚本已设 `PUPPETEER_SKIP_DOWNLOAD=true` 并把 Chromium 写进临时 puppeteer 配置；本地 `npm install` 时同样要设（puppeteer postinstall 会被 npm allow-scripts 拦下，属正常）。
3. **LR vs TB 比例**：`flowchart LR` 常极宽（如 6549×1068），压到页宽后文字偏小；16:9 嵌图优先 `TB` 紧凑版（短标签 + `fontSize 20px+`），或图左 + 图例右的布局。
4. **中文**：系统「微软雅黑」渲染正常；别用纯拉丁字体栈。
5. **文本模型看不到图**：渲染成功 ≠ 效果达标——导出后请用户目视确认（或截图给用户看）。
6. **离线可用**：本地安装目录 `.opencode/tools/mermaid/`（`npm install` 一次即可）；npx 回退会联网取 `@mermaid-js/mermaid-cli@11.17.0`。

## 安装 / 修复

```powershell
# 本地渲染器（已装；重装用）
cd .opencode/tools/mermaid
$env:PUPPETEER_SKIP_DOWNLOAD='true'; npm install --no-fund --no-audit

# 浏览器缺失时
npx playwright install chromium
```

## 产物约定

- 分享/交付图放目标目录（如项目人读区 `.local/assets/`）；临时试验放 `%TEMP%\opencode`。
- 同时保留 `.mmd` 源文件（可再生成）；嵌入 PPT 后源图仍可追溯。
