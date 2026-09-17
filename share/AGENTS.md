# AGENTS.md

本文件的说明供 opencode 助手在任何项目下执行任务时参考（工作区公共层）。本文件位于 `.opencode/`（junction → 本仓库 `share/`）；项目根 `opencode.json` 需以 `instructions: [".opencode/AGENTS.md"]` 引入后生效。

## 公共层治理

- 本层内容（本文件、agent/skills/command/tools/runbooks/opencode.json）**对所有挂载项目生效**；进入/修改准则见 `.opencode/GOVERNANCE.md`。
- 修改须先评估影响面并按两级门审核确认后提交；**禁止把本机/项目具体值写回本层**；改动后需重启 opencode 生效。
- **可选组件按机器启用**：看板（pm-bot/kb.py）、mockoon、pen、codegraph、session-spawn 等以各机器实际安装为准；未启用的组件应关闭对应 agent/入口（见 `INSTALL.md` §5.1），不得按"已启用"假设行事。

## 口令表（工作区公共 · 持续扩充）

> 口令 = 用户说出的固定触发词，映射到一个确定的动作/对象。听到口令即按本表执行，不当作普通词汇理解；新增口令在表尾追加一行。

| 口令 | 含义 | 动作 |
|---|---|---|
| 美工 | 视觉设计执行器 | 委派子 agent **pen-designer**（task 工具）执行视觉任务（生成/修改 .pen、导出 PNG） |
| 执行任务书 | 施工单执行 | 读指定任务书文件全文（默认任务书目录由项目 AGENTS.md 声明），按其「执行步骤/验收/边界」执行并回填「执行记录」；机制见该目录 README.md |
| 生成mock | Mockoon 环境生成 | 加载 skill **mockoon-env**（`.opencode/skills/mockoon-env/`），按项目契约生成/维护 Mockoon 环境 JSON；改完必跑 `mockoon-cli validate`（本机未装 mockoon 时跳过） |
| 开发组 | 编码编排（leader / coder / tester / reviewer） | 切到 `leader` agent，按工作区编排实例入口（默认 `<工作区>/orchestration/README.md`，路径由工作区 AGENTS.md 声明；机制全文见 skill **orchestration**）执行；实例为独立本地 git 仓库，产物提交到该仓库；非 leader 会话收到此口令先提示切换（Tab） |
| 产品 | 产品分析师（需求 / 验收 / 待定项） | 切到 `analyst` agent；维护 docs/00/01/05 与待定项清单，不聊实现、不臆造需求、不替人拍板 |
| mermaid | mermaid 渲染 | 加载 skill **mermaid-render**，用 `.opencode/tools/mermaid-render.mjs` 渲染/嵌入图（复用 Playwright Chromium，零额外浏览器下载） |

## 任务书（施工单）

- **触发**：用户说「执行任务书 <路径>」或要求按任务书施工时。
- **流程**：读任务书目录 `README.md`（机制与索引）→ 读任务书全文 → 只读任务书「必读」列出的文件（勿扩读）→ 按步骤执行 → 逐条跑「验收」→ 回填「执行记录」并更新索引状态 → 按「收尾」提交。
- **纪律**：不扩范围、不猜路径；与任务书不符的事实即停并记录；密钥只写位置不写值；同一验收项失败 2 次即停。

## 分支与提测纪律（通用）

> 多仓项目通行的分支/提测纪律；具体仓库与版本线映射由项目 AGENTS.md 声明。

- **两闸门**：需求合并到提测分支前，必须**同时**满足 ① 人工审核确认 ② 开发环境自测通过；未过闸门前只落 dev/主干，不得合并到提测分支。
- **定稿一次性合并**：开发过程中禁止每改一轮就 cherry-pick 到提测分支；需求定稿后一次性合入。
- **自测提交收敛**：同一轮连贯的「修改→测试→修改」在推送前 squash/amend 为单提交；一个需求尽量只留一个提交。
- **已进提测分支不合并/不改写**：相关提交已被挑选到提测分支的，不再合并或改写（避免分叉与 force-push）。
- **合并姿势**：`git cherry-pick --no-commit <base>..<head>` 生成单个提交推提测分支；共享分支**禁止 force-push**。
- **落地前必读需求原文 + 附件截图并逐条对照**（防端/父级/位置/命名返工）。
- **成套挑选**：按「需求/BUG = 一组提交」（代码+测试+文档）成套 pick，跳过 `git 忽然`、`临时发包` 等垃圾提交；提交信息带需求/缺陷编号便于追溯。

## 多线同步核查（同一语义改动）

> 适用于 dev / 提测等多条代码线已分叉的项目（同名方法、同字段的实现可能不同）。

- **禁止把一线验证过的替换清单直接套另一线**；每条线独立全仓核查。
- 核查须覆盖同一语义的**全部调用形态**：直接枚举 API、扩展方法（含带 cast 的 `((T)x).GetDescription()`）、`ToString()`、**同一语义的另一个枚举**。
- grep 用宽松模式（行内同时含枚举名与目标方法名）再人工筛，避免漏掉 cast/中间变量形态。
- 验证以**目标线实际部署环境**为准（dev 验证 ≠ 提测线生效）。

## 提测/发布前置确认（触发构建前必做）

触发构建前向用户输出三行并获确认：

1. **范围**：本次涉及哪几个 Job/仓库，哪些有改动、哪些仅重打；
2. **分支头**：各仓 `git log origin/{分支} -1` 的 HEAD + 最近提交清单；
3. **他人提交提示**：分支上非本次需求的他人提交（会一并进包）显式列出。

> 触发前先确认代码已推送：`git log --oneline origin/{分支}..{分支}` 输出为空；本地 commit 不 push 不会进包。

## 前端产物纪律（产物目录入库时）

- **源码与产物分开两笔提交**：仅 `src/` 一笔；`npm run build` 重产产物目录后仅产物目录一笔。
- **改源码必须重新 build**；提交前特征串自检：`grep -r "<本次改动特征串>" <产物目录>/`，无命中 = 没 build，禁止提交/推送。
- **跨线挑选不 pick 产物**：产物在目标线重新构建提交（源分支产物可能携带其它需求）。
- 构建 hash 全量替换、小图内联为 base64 属正常现象。

## PDF 解读工具

- **触发**：用户发送 PDF 文件，或说「读一下这个 PDF」「解读这个 PDF」「把 PDF 转成 Markdown」时，直接使用，无需询问。
- 脚本位置：`.opencode/tools/pdf2md.py`

### 用法表

| 需求 | 命令 |
|------|------|
| 解读 PDF | `py .opencode/tools/pdf2md.py 文档.pdf` |
| 写入 UTF-8 文件（中文不乱码） | `py .../pdf2md.py 文档.pdf -o 结果.md` |
| 批量 | `py .../pdf2md.py a.pdf b.pdf` |
| 只要分类 | `py .../pdf2md.py 文档.pdf --detect-only --verbose` |
| 扫描版不 OCR | `py .../pdf2md.py 扫描件.pdf --no-ocr` |
| 保留分页 | `py .../pdf2md.py 文档.pdf --pages` |

### 注意事项

- 用 `py` 运行（Windows 启动器；直接 `python` 可能是 WindowsApps 存根）；需装 pdf-inspector / pymupdf / rapidocr-onnxruntime（本机解释器路径见机器层 `~/.config/opencode/AGENTS.md`）。
- OCR 默认 200 DPI，可 `--dpi 300` 调高；缺包时 `py -m pip install pdf-inspector pymupdf rapidocr-onnxruntime`。

## pen.dev 设计（两种接入）

- **触发**：用户要生成/修改设计稿、mockup、UI、海报、导出图片，或提到 `.pen`、pen.dev、pencil 时，加载 `pen-design-headless` skill（`.opencode/skills/pen-design-headless/`）。
- **路线 A（无头生成，默认）**：opencode 当前模型当设计师，pen.dev CLI 仅作渲染引擎（不经过 Claude）。用 `.opencode/tools/pen-exec.mjs` 驱动，例如
  `node .opencode/tools/pen-exec.mjs --file ./designs/hero.pen --cmds-file cmds.txt --clean`；
  每条命令须是交互式 shell 工具调用（`execute({ input: '...' })`），详见 skill。
- **路线 B（实时编辑）**：设计已在 VS Code 的 pen.dev 编辑器里打开时，用已连通的 `pencil` MCP 工具实时改画布（见机器层 `opencode.json` 的 `mcp.pencil`）。
- **成批画板生成/修改**：优先委派子 agent **pen-designer**（`.opencode/agent/pen-designer.md`，task 工具；口令「美工」见表）执行落地 + 自检 + 导出；主 agent 保留规约评审、文档同步与提交。踩坑与自检清单见 `.opencode/skills/pen-design-headless/reference/troubleshooting.md`。
- 认证与限制：无头路线需要 `PEN_CLI_KEY`（机器层用户级环境变量）或 `pen login`；未安装 Pen CLI 的本机跳过本节。文本模型无法读图，导出 PNG 后用 `Get`/`ctx.problems` 结构化自检，并请用户目视确认。

## 基础设施 Runbooks

- 目录：`.opencode/runbooks/`（索引见 `README.md`；当前无自建服务，清单为空）。
- **触发词**：涉及 `WSL`/`WSL2` 服务运维、`runbook`、自建基础设施（备份/升级/重启/排障）时，先读取对应 runbook 全文，再按其中命令操作，勿凭记忆。
- runbook 属**机器事实区**：换机必须整目录重写，不得保留标着「运行中」的失真记录。
- 对运行环境做了实质改动后，同步更新对应 runbook 的「最近更新」。

## 看板 PM 协作（pm-bot）

- 已部署看板的本机：用专用子 agent **pm-bot**（模型 `opencode/big-pickle`，`.opencode/agent/pm-bot.md`）做 Kanboard PM 操作；**触发词**：看板、任务卡、建卡/移列/加评论/按 FR 查。
- 工具：`.opencode/tools/kb.py`；凭据在 `~/.config/opencode/kanboard.env`（机器层，勿入库）；pm-bot 只做模板化读写，删除/改权限等高危操作一律人工。
- **未部署看板的本机**（无 runbook、无 `kanboard.env`）：在机器层禁用 pm-bot（`agent.pm-bot.disable`，见 `INSTALL.md` §5.1），勿凭记忆操作。

## 数据库设计（db-designer skill）

- 工作区已装通用版 **db-designer** skill（`.opencode/skills/db-designer/`），涉及新建表、增改 ERD（.erd.json）、生成 DDL 时加载它，无需子 agent。
- 产出约定：ERD 用 ERD Editor v3 格式（`doc/2-database-design/增量/{序号}-{主题}.erd.json`，目录约定随项目调整）；DDL 为 MySQL 8.x（InnoDB/utf8mb4，每列必带 COMMENT）。
- 每份 `.erd.json` 须配套同名数据字典 `.md`（只读，勿手改），由 `.opencode/skills/db-designer/tools/erd2md.py` 从 erd.json 生成；改 ERD 后重跑该脚本刷新。
- 项目内优先按该项目已有 ERD/设计文档目录约定输出，无约定时用默认路径。

## Mock 服务（mockoon-env skill）

- **@mockoon/cli**（Node ≥18）与 `mockoon` MCP（`mockoon-cli mcp`，工具 `list_mocks`/`start_mock`/`stop_mock`/`list_running_mocks`）属**机器层**配置；未安装/未注册的本机跳过本节（见 `INSTALL.md` §5）；`MOCKOON_DATA_DIRS` 指向项目 mock 目录。
- **触发**：生成/修改 Mockoon 环境 JSON、起停 mock 服务、联调打桩时，加载 skill **mockoon-env**（`.opencode/skills/mockoon-env/`）——含 v9 schema 参考、常用模板（多响应规则/回调）、validate 与冒烟流程。
- 项目约定：mock 环境文件随仓（如 `mock/environments/`），CLI 版本与端口登记在该目录 `README.md`；改完环境 JSON 必须 `mockoon-cli validate`。
