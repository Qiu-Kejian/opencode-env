# AGENTS.md

本文件的说明供 opencode 助手在任何项目下执行任务时参考（工作区公共层）。本文件位于 `.opencode/`（junction → 本仓库 `share/`）；项目根 `opencode.json` 需以 `instructions: [".opencode/AGENTS.md"]` 引入后生效。

## 公共层治理

- 本层内容（本文件、agent/skills/command/tools/runbooks、opencode.json）**对所有挂载项目生效**；进入/修改准则见 `.opencode/GOVERNANCE.md`。
- 修改须先评估影响面并按两级门审核确认后提交；**禁止把本机/项目具体值写回本层**；改动后需重启 opencode 生效。

## 口令表（工作区公共 · 持续扩充）

> 口令 = 用户说出的固定触发词，映射到一个确定的动作/对象。听到口令即按本表执行，不当作普通词汇理解；新增口令在表尾追加一行。

| 口令 | 含义 | 动作 |
|---|---|---|
| 美工 | 视觉设计执行器 | 委派子 agent **pen-designer**（task 工具）执行视觉任务（生成/修改 .pen、导出 PNG） |
| 执行任务书 | 施工单执行 | 读指定任务书文件（默认工作区 `taskbooks/`，具体路径见项目 AGENTS.md）全文，按其「执行步骤/验收/边界」执行并回填「执行记录」；机制见该目录 README.md |
| 生成mock | Mockoon 环境生成 | 加载 skill **mockoon-env**（`.opencode/skills/mockoon-env/`），按项目契约生成/维护 Mockoon 环境 JSON；改完必跑 `mockoon-cli validate` |
| 开发组 | 编码编排（leader / coder / tester / reviewer） | 切到 `leader` agent 按项目编排入口（默认 `orchestration/README.md`，由项目 AGENTS.md 声明）执行；非 leader 会话收到此口令先提示切换（Tab） |
| 产品 | 产品分析师（需求 / 验收 / 待定项） | 切到 `analyst` agent；维护 docs/00/01/05 与待定项清单，不聊实现、不臆造需求、不替人拍板 |
| mermaid | mermaid 渲染 | 加载 skill **mermaid-render**，用 `.opencode/tools/mermaid-render.mjs` 渲染/嵌入图（复用 Playwright Chromium，零额外浏览器下载） |

## 任务书（施工单）

- **触发**：用户说「执行任务书 <路径>」或要求按任务书施工时。
- **流程**：读任务书目录 `README.md`（机制与索引）→ 读任务书全文 → 只读任务书「必读」列出的文件（勿扩读）→ 按步骤执行 → 逐条跑「验收」→ 回填「执行记录」并更新索引状态 → 按「收尾」提交。
- **纪律**：不扩范围、不猜路径；与任务书不符的事实即停并记录；密钥只写位置不写值；同一验收项失败 2 次即停。

## PDF 解读工具

- **触发**：用户发送 PDF 文件，或说「读一下这个 PDF」「解读这个 PDF」「把 PDF 转成 Markdown」时，直接使用，无需询问。
- 脚本位置：`.opencode/tools/pdf2md.py`

### 用法表

| 需求 | 命令 |
|------|------|
| 解读 PDF | `python .opencode/tools/pdf2md.py 文档.pdf` |
| 写入 UTF-8 文件（中文不乱码） | `python .../pdf2md.py 文档.pdf -o 结果.md` |
| 批量 | `python .../pdf2md.py a.pdf b.pdf` |
| 只要分类 | `python .../pdf2md.py 文档.pdf --detect-only --verbose` |
| 扫描版不 OCR | `python .../pdf2md.py 扫描件.pdf --no-ocr` |
| 保留分页 | `python .../pdf2md.py 文档.pdf --pages` |

### 注意事项

- 必须用 `python` 运行，且已装好 pdf-inspector / pymupdf / rapidocr-onnxruntime 依赖（本机解释器路径见机器层 `~/.config/opencode/AGENTS.md`）。
- OCR 默认 200 DPI，可 `--dpi 300` 调高；依赖 `pdf-inspector`、`pymupdf`、`rapidocr-onnxruntime`，缺包时用 `python -m pip install pdf-inspector pymupdf rapidocr-onnxruntime` 安装。

## pen.dev 设计（两种接入）

- **触发**：用户要生成/修改设计稿、mockup、UI、海报、导出图片，或提到 `.pen`、pen.dev、pencil 时，加载 `pen-design-headless` skill（`.opencode/skills/pen-design-headless/`）。
- **路线 A（无头生成，默认）**：opencode 当前模型当设计师，pen.dev CLI 仅作渲染引擎（不经过 Claude）。用 `.opencode/tools/pen-exec.mjs` 驱动，例如
  `node .opencode/tools/pen-exec.mjs --file ./designs/hero.pen --cmds-file cmds.txt --clean`；
  每条命令须是交互式 shell 工具调用（`execute({ input: '...' })`），详见 skill。
- **路线 B（实时编辑）**：设计已在 VS Code 的 pen.dev 编辑器里打开时，用已连通的 `pencil` MCP 工具实时改画布（见全局 `~/.config/opencode/opencode.json` 的 `mcp.pencil`；MCP 为机器层配置）。
- **成批画板生成/修改**：优先委派子 agent **pen-designer**（`.opencode/agent/pen-designer.md`，task 工具；口令「美工」见表）执行落地 + 自检 + 导出；主 agent 保留规约评审、文档同步与提交。踩坑与自检清单见 `.opencode/skills/pen-design-headless/reference/troubleshooting.md`。
- 认证：无头路线需要 `PEN_CLI_KEY`（已写入用户级环境变量）或 `pen login`；`pen --prompt` 走 pen 内置 Claude agent，deepseek 不用它。
- 注意：文本模型（如 deepseek-v4-flash）无法读图，导出 PNG 后用 `Get`/`ctx.problems` 结构化自检，并请用户目视确认。

## 基础设施 Runbooks

- 目录：`.opencode/runbooks/`（索引见 `README.md`）。
- **触发词**：涉及 `kanboard`、`WSL`/`WSL2` 服务运维、`runbook`、自建基础设施（备份/升级/重启/排障）时，先读取对应 runbook 全文，再按其中命令操作，勿凭记忆。
- runbook 涉及的服务（如 Kanboard v1.2.54 @ WSL2/Ubuntu 22.04，`http://localhost`）详情见 `kanboard-wsl.md`；pm-bot（维护该 Kanboard 看板，由 `opencode/big-pickle` 驱动）见 `llm-pmbot.md`。
- 对运行环境做了实质改动后，同步更新对应 runbook 的「最近更新」。

## 看板 PM 协作（pm-bot）

- 本机 Kanboard 看板（项目名见 `kanboard.env` / 看板实际）的 PM 操作用专用子 agent **pm-bot**（模型 `opencode/big-pickle`，`.opencode/agent/pm-bot.md`）。
- **触发词**：需要维护看板/任务卡（建卡/移列/加评论/按 FR 查）时，可把操作交给 pm-bot 执行，或直接用 `.opencode/tools/kb.py`（命令见 `runbooks/llm-pmbot.md`）。
- 凭据在 `~/.config/opencode/kanboard.env`（机器层），pm-bot 只做模板化读写；删除/改权限等高危操作一律人工。

## 数据库设计（db-designer skill）

- 工作区已装通用版 **db-designer** skill（`.opencode/skills/db-designer/`），涉及新建表、增改 ERD（.erd.json）、生成 DDL 时加载它，无需子 agent。
- 产出约定：ERD 用 ERD Editor v3 格式（`doc/2-database-design/增量/{序号}-{主题}.erd.json`，目录约定随项目调整）；DDL 为 MySQL 8.x（InnoDB/utf8mb4，每列必带 COMMENT）。
- 每份 `.erd.json` 须配套同名数据字典 `.md`（只读，勿手改），由 `.opencode/skills/db-designer/tools/erd2md.py` 从 erd.json 生成；改 ERD 后重跑该脚本刷新。
- 项目内优先按该项目已有 ERD/设计文档目录约定输出，无约定时用默认路径。

## Mock 服务（mockoon-env skill）

- 已装 **@mockoon/cli 9.8.0**（Node ≥18）；全局层 `opencode.json` 注册 `mockoon` MCP（`mockoon-cli mcp`，工具 `list_mocks`/`start_mock`/`stop_mock`/`list_running_mocks`，MCP 属机器层配置），`MOCKOON_DATA_DIRS` 指向项目 mock 目录；改 MCP 配置后需重启 opencode。
- **触发**：生成/修改 Mockoon 环境 JSON、起停 mock 服务、联调打桩时，加载 skill **mockoon-env**（`.opencode/skills/mockoon-env/`）——含 v9 schema 参考、常用模板（多响应规则/回调）、validate 与冒烟流程。
- 项目约定：mock 环境文件随仓（如 `yuantoubao/mock/environments/`），CLI 版本与端口登记在该目录 `README.md`；改完环境 JSON 必须 `mockoon-cli validate`。
