# pen 无头执行 · 踩坑与验证清单

> 来自 `00.1-宝宝档案.pen`（15 屏）实战。用 `tools/pen-exec.mjs` 驱动前先读本文件。

## 1. 命令解析（pen-exec / cmds-file）

- cmds 文件每行必须是交互式工具调用：`execute({ input: '…' })`；裸 JS 行会被拒绝。
- 一行内多语句用 `;` 保持单行；`save()`/`exit()` 由 helper 自动追加。
- **嵌套数组字面量 `[[…]]` 会报 SyntaxError**（引擎解析器限制）。替代方案：
  - 扁平化：`for(const s of "a|b,c|d".split(",")){ const a=s.split("|"); … }`
  - 或拆成多条 `execute` 逐条写。
- 含引号/中文的命令用 `--cmds-file` 写文件再跑，避免 PowerShell 引号问题。
- 一个 helper 调用 = 一个会话；globals（不带 `const`/`let` 的变量）只在会话内持久。跨会话复用节点：先 `Print(id)` 固化，或 `Get(n=>n.name==="…")` 找回。
- 单个 `execute` 失败只回滚该次调用，后续行继续；不要把关键逻辑塞进一个巨型调用。

## 2. 图标（lucide 名称随版本变）

已验证的坑：

| 失效名 | 正确名 |
|---|---|
| `more-horizontal` | `ellipsis` |
| `alert-circle` | `circle-alert` |
| `check-circle` | `circle-check` |

常用且可用：`signal` `wifi` `battery-full` `chevron-left` `chevron-right` `chevron-down` `baby` `check` `plus` `lock` `copy` `message-circle` `moon` `file-text` `user` `circle-alert` `circle-check`。

插入后若引擎回 `Icon 'x' was not found in the 'lucide' icon set`，用 `Update(id,{icon:"正确名"})` 修复。

## 3. 布局与告警

- 空 frame 先插入再填子节点，会报 `Collapsed size …`；填完后自动消失，最后统一自检确认。
- 文本必须有 `fill`（引擎不继承颜色）；图标需 `fill` 才可见。
- 自检三连：
  - 裁切/越界：`Get((n,c)=>{ if(c.problems) Print(n.name,"|",c.parentCtx?c.parentCtx.node.name:"root","|",c.problems) })`
  - 内容区溢出（内容区高 724）：`Get((n,c)=>{ if(c.parentCtx && c.parentCtx.node.name==="Content" && c.bounds.y+c.bounds.height>724) Print("OVERFLOW",n.name) })`
  - 缺 fill：`Get(n=>n.type==="text"&&!n.fill?Print("NO FILL:",n.name):undefined)`
- 标准画板 375×812：状态栏 44 + 导航栏 44 → 内容区 724。

## 4. 画布组织

- 根级画板用显式 `x/y` 排布；`FindEmptySpace({width:375,height:812,direction:"right",padding:60})` 链式放屏。
- 中间插屏：先右移后续画板再插入：
  ```js
  const bs=Get((n,c)=>c.depth===0&&n.type==="frame"&&c.bounds.x>TH?n.id:undefined);
  for(const id of bs){ Update(id,{x:Get(id,{depth:0}).x+Δ}) }
  ```
- 组件放画板左侧固定槽位（如 x=0/400/800），避免与画板抢空间。

## 5. 组件模式（reusable + ref descendants）

```js
navBarId=Insert(document,{type:"frame",name:"NavBar",reusable:true,x:400,y:0,width:375,height:44,layout:"horizontal",alignItems:"center",fill:"$surface"})
navTitleId=Insert(centerId,{type:"text",name:"Nav Title",content:"标题",fontFamily:"$font-ui",fontSize:16,fontWeight:"600",fill:"$ink"})
// 实例 + 文案覆盖（覆盖键用组件内子节点 ID）：
Insert(boardId,{type:"ref",ref:navBarId,name:"NavBar",width:375,height:44,descendants:{[navTitleId]:{content:"宝宝资料"}}})
```

- 组件根给固定尺寸；实例可 `width:"fill_container"` 覆盖。
- 覆盖键可用子节点 ID 或唯一 name；同名多节点时必须用 ID。

## 6. 导出

- `Export([...ids],"png","<dir>",{scale:2})` 输出按 nodeId 命名（如 `xjnKO.png`）→ 必须 `Move-Item` 重命名为 `<编号>-<名称>.png`。
- 文本模型读不了图：导出后交人工目视；不要用 `TakeScreenshot`。
- 项目若在 `.gitignore` 忽略 `exports/`（如 yuantoubao），导出图不入库，仅提交 `.pen` 与文档。

## 7. 单写者

同一 `.pen` 不并行：一个 helper 会话「打开 → 改 → 保存」期间，其他写会互相覆盖。多文件（如 00.2 / 00.3）可并行，同一文件不可。
