# opencode-env

opencode 公共配置环境仓库（agents / skills / AGENTS.md 等），跨项目、跨机器共享。

- 仓库根：本文档 + 工作区工具文件
- `share/`：**真正的配置挂载层**（agents/、skills/、AGENTS.md）——各项目根用目录联接（junction）挂到 `.opencode` 时，指向的是 `share/`
- 目的：把「多项目共享的公共配置」从各项目目录里抽出来，单一 git 来源，远程同步，多机迁移

> **文档地图**：本文档 = 设计原理与结构；`INSTALL.md` = 新机/新项目引导安装（opencode 可读可执行，含参数收集与验收）；`share/GOVERNANCE.md` = 公共层进入/修改准则（两级审核门）。

## 为什么拆两层（README 与挂载内容分离）

junction 是目录级链接——若项目根 `.opencode` 直接指向仓库根，仓库根里的 `README.md` 等文件会透过 `.opencode\` 出现在项目根文件树中。

因此仓库拆 **仓库根（文档/工作区）** 与 **`share/`（挂载内容）** 两层：

```
<repo-root>\                   ← git 仓库（README 在这里，人可打开看）
├── README.md                 ← 本文档（不进入任何项目根）
├── .gitignore
└── share\                    ← 挂载层（junction 目标在这里）
    ├── AGENTS.md             ← 公共规则
    ├── agents\               ← 公共 agent 定义
    └── skills\               ← 公共技能
```

项目根 `.opencode` → junction → `<repo-root>\share`，README 完全不可见。

> 约定：`<repo-root>` = 本仓库的克隆位置；`<project-root>` = 挂载它的项目根；`<legacy-config-dir>` = 旧机配置目录。

## 目录结构与可入库边界

opencode 的 `.opencode` 目录承载以下内容（均为纯文本，天然可 git 管理）：

| 子目录 | 内容 | 可入库 |
|--------|------|--------|
| `agents/`（或 `agent/`） | 自定义 agent 定义（.md frontmatter + prompt） | ✅ |
| `skills/`（或 `skill/`） | 技能（`SKILL.md` + 辅助脚本） | ✅ |
| `commands/`（或 `command/`） | 斜杠命令（`/xxx` prompt 模板） | ✅ |
| `plugins/`（或 `plugin/`） | 本地插件 .ts/.js | ✅（node_modules 除外） |
| `modes/` | 模式定义 | ✅ |
| `themes/` | 主题 | ✅ |
| `tools/` | 自定义工具 | ✅ |
| `opencode.json` | 项目级配置（可选） | ✅ |

**唯一不可入库的边界**：`node_modules/`、`package.json`、`package-lock.json`、`bun.lock`（依赖）——被 `.gitignore` 排除。

## 配置分层模型

opencode 的规则与配置按物理目录层级分层，全部 **merge（deep merge）+ instructions 拼接（concat + Set 去重）**，非覆盖。**ocbase 公共配置必须挂在「项目层」（代码仓库的上一层），不能更往上**——这是相对路径成立的前提：

```
┌─ ① 深度层      各 git/svn 代码仓库内 .opencode / AGENTS.md    ← 与代码同源，随仓库版本控制
│
├─ ② 项目层       项目根 .opencode → junction → 本仓库 share/    ← ★ 外置公共层（ocbase 挂在项目根这一级）
│                 ↑ 项目根 = 代码仓库的上一层，相对路径成立的关键
│                 项目根同时可有自己的 AGENTS.md / opencode.json
│
├─ ③ 定制层(可选) 项目根上一级（或多项目公共父目录）的 .opencode  ← 个性化定制，真实目录
│                 ↑ 某些项目/某组项目需要定制时，在此加一层，按需存在、不加就没有
│
├─ ④ 全局层      ~/.config/opencode/                            ← 个人/机器全局
└─ ⑤ 世界层(兜底) ~/.claude/CLAUDE.md 等                        ← Claude Code 兼容
```

关键点：

- **ocbase 是「外置公共层」**：内容抽取到独立 git 仓库，每个项目根用 junction 引用它，等价于"外置的共享目录"。公共配置物理上落在项目根 `.opencode`，所以 `.opencode/...` 相对引用在项目根及其下所有代码仓库内都成立。
- **个性化定制不塞进公共层**（否则污染共享仓库），而是**加一层真实目录**（定制层，位于项目层与全局层之间）。多级收集机制天然支持——某项目要定制就加，不要就不加。
- **相对路径成立的条件**：配置里以 `.opencode/...` 开头的相对引用，是从项目根解析的。挂得越深（越靠近项目根），深度层代码仓库引用公共配置的相对路径越短越稳定；挂到项目根上一级，深度层引用会跨级破坏。
- 深度层（代码仓库内）的 AGENTS.md **不会自动向下索引**，只有 `instructions` glob（如 `packages/*/AGENTS.md`）显式引入才进上下文。

### instructions 数组拼接

`opencode.json` 的 `instructions` 在不同 config 源之间是**拼接 + 去重**（源码 `mergeConfigConcatArrays`：`Array.from(new Set([...target.instructions, ...source.instructions]))`），全局在前、项目在后。所以：

```jsonc
// 项目根 opencode.json
{ "instructions": [".opencode/AGENTS.md", "AGENTS.md"] }
```

会把公共 AGENTS.md（经 `.opencode` junction）与项目根自定义 AGENTS.md 都拼进上下文。语法同时支持 glob（`packages/*/AGENTS.md`）与远程 URL。

建议用相对路径 `.opencode/AGENTS.md` 而非绝对路径——junction 让仓库恰好挂在 `.opencode` 下，相对引用天然跨机器、换盘符零改动。

## 多级 .opencode 收集机制（关键源码事实）

`ConfigPaths.directories` 不是只认一层 `.opencode`，而是**从会话目录向上逐级收集**，全部进配置目录列表：

```ts
return unique([
  Global.Path.config,               // ① 全局 ~/.config/opencode
  ...afs.up({ targets: [".opencode"], start: directory, stop: worktree }),   // ② 从会话目录向上逐级找 .opencode
  ...afs.up({ targets: [".opencode"], start: Global.Path.home, stop: home }),// ③ HOME 下的 .opencode
  ...(Flag.OPENCODE_CONFIG_DIR ? [Flag.OPENCODE_CONFIG_DIR] : []),           // ④ OPENCODE_CONFIG_DIR
])
```

- 每级 `.opencode` 的 agents/、skills/、commands/、plugins/ 是**按目录各扫各的、名字空间合并**——同名 agent/skill 冲突、不同名并存。
- ⚠️ **worktree 边界坑**：`afs.up` 的 `stop` 是 git worktree 根。若某项目根**本身是 git 仓库**，向上收集到该项目 git 根为止，**更上层的公共 `.opencode` 不会生效**。对非 git 项目根（SVN/杂项目录）则能向上收到公共层。
  - 对策：git-root 项目单独 junction 一个 `.opencode` 到本仓库 `share/`；或设全局 `OPENCODE_CONFIG_DIR`。

## junction 挂载方式（Windows，无需管理员）

```powershell
# 新机/新项目：克隆公共仓库到固定路径
git clone <remote> <repo-root>

# 项目根挂载 .opencode
mklink /J "<project-root>\.opencode" "<repo-root>\share"
Remove-Item "<project-root>\.opencode"        # 若已存在真实目录先删除
```

跨平台注意：junction 是 NTFS 特性；macOS/Linux 用 `ln -s`（symlink），仓库结构不变、挂载方式不同。

## 与 OPENCODE_CONFIG_DIR 对比

| 方式 | 选择性挂载 | `.opencode/...` 相对引用 | 受 worktree 边界影响 | 官方机制 |
|------|:---:|:---:|:---:|:---:|
| junction（本仓库方案） | ✅ 按项目控制 | ✅ 全链路可用 | ⚠️ git-root 项目断链 | 系统级，非 opencode 概念 |
| `OPENCODE_CONFIG_DIR` env | ❌ 全局生效 | ❌ 需改引用 | ❌ 不受影响 | ✅ 官方一等公民 |

`OPENCODE_CONFIG_DIR` 指向仓库根时，opencode 像扫 `.opencode` 一样扫描它，且加载顺序在项目 `.opencode` 之后（可覆盖），作为第四个 sources 无条件生效。缺点是对所有项目生效、且在 `directories` 中排最后。

## 技能审计清单（TODO：逐项审计后入 share/）

以下内容当前在 `<legacy-config-dir>\.opencode`，**尚未审计入仓**，逐项评估后移入 `share/`：

- [ ] `agents/`：assistant / coder / coder-pro / lead / planner / reviewer / tester / uidesigner（8 个 .md）
- [ ] `skills/`：browser-automation / create-project-from-requirement / daily-review / de-aiify / import-zentao / inbox-processor / kefu-demand-flow / mockoon-config-gen / morning-plan / prep-meeting / process-meeting / research-assistant / sync-gtd-status / sync-smart-service / test-env-prep / thinking-partner / ui-designer / update-zentao-data / weekly-synthesis / weekly-zentao-report / work-handoff / yxxg-assign-dev（22 个）
- [ ] `AGENTS.md`：公共规则是否入 `share/`
- [ ] `commands/`：尚无，目录预留
- [ ] ⚠️ 待审要点：skills 内硬编码绝对路径（`<legacy-config-dir>` 之类）在迁移后是否失效，需逐项核对或改造为相对引用

审计完成后更新本文档与 git 提交。

## 本机审计与迁移记录（2026-09-14）

> 以下为本机（qiu_k / D: 盘）实际情况；上方「技能审计清单」属于另一条机器的记录，保持原样。

### 来源与去向

| 来源 | 去向 | 内容 |
|---|---|---|
| `~/.config/opencode/`（全局层） | `share/` | AGENTS.md、agent（pen-designer、pm-bot）、command、skills（16）、tools（5 脚本 + mermaid/）、runbooks（4）；全局仅保留 MCP、`external_directory` 白名单、安全红线、`kanboard.env` 等机器层 |
| `D:\dev\bbcare\.opencode\` | `share/agent/`（泛化） | leader / coder / tester / reviewer / analyst / tester-alt / reviewer-alt（.bak 未迁） |
| 新写 | `share/opencode.json` | 通用权限段（env/ssh deny 等）+ 插件（codegraph / session-spawn）+ ollama provider |
| 新写 | `share/skills/taskbook/`、`share/skills/orchestration/` | 机制模板（实例留在 bbcare / yuantoubao 仓库） |

- 有意未迁移：field-agent agent、`D:\qb` sleep-stats、上游仓库自带 `.opencode`（`D:\dev\src\opencode`）、secrets/.env、logs/state/node_modules、`.backup` 快照。
- 备份：`D:\dev\bbcare\.backup\opencode-config-20260914\`（含回滚步骤 `MANIFEST.md`；验收通过前勿删）。
- 新增文档：`INSTALL.md`（引导安装）、`install/`（机器/项目配置模板）、`share/GOVERNANCE.md`（公共层治理）；机器层 `~/.config/opencode/AGENTS.md`（本机个性化，不入库）。

### 挂载现状与新增挂载清单

| 挂载点 | 目标 | 配套 |
|---|---|---|
| `D:\dev\bbcare\.opencode` | `D:\oce\opencode-env\share`（junction） | `D:\dev\bbcare\opencode.json`：`.local` ask 规则 + `instructions: [".opencode/AGENTS.md"]` |
| `D:\oce\opencode-env\.opencode` | `share`（junction，自挂载） | 仓库根 `opencode.json`：`instructions` |

新项目挂载三步：
1. `cmd /c mklink /J "<项目根>\.opencode" "D:\oce\opencode-env\share"`
2. 项目根 `opencode.json` 加 `"instructions": [".opencode/AGENTS.md"]`（项目级权限/规则按需另加，注意宽规则在前、窄规则在后）
3. 重启 opencode 后验证：agent / skills 可发现、`.opencode/tools/*` 可运行、`*.env` deny 生效

### 注意

- `.gitignore` 已重新纳入 git 跟踪（原来自忽略），新增 `.opencode/`、`share/state/`、`share/logs/`；`share/.gitignore` 为 opencode 运行时保障文件（含 mermaid 依赖清单例外），已入库。
- opencode 启动会在 junction 目标（`share/`）与机器层（`~/.config/opencode/`）内生成 `package.json` / `package-lock.json` / `node_modules` / `state/` / `.gitignore` 等运行时文件，均已忽略，勿当死重清理。
- 跨机迁移需核对运行环境：模型可用性（`deepseek/deepseek-v4-flash`、`opencode/big-pickle`）、Pen CLI（`PEN_CLI_KEY`）、Python/Minconda 依赖、Playwright Chromium、Mockoon CLI、DBX、Ollama。
- 配置不热加载：迁移或改动后必须重启 opencode。

### 迁移修复记录（2026-09-14）

- **A3 路径中性化**（提交 `ec5c143`）：`share/agent/pen-designer.md` 临时目录改指机器层声明；`share/skills/mockoon-env/reference/cli-cheatsheet.md` MCP 示例改占位符并修正 `env`→`environment`。
- **B1 公共层白名单**：机器层 `external_directory` 增 `D:/oce/opencode-env/**`（挂载项目经 junction 编辑 `.opencode/...` 按真实路径判定）；`install/machine.opencode.json.template` 增 `{{REPO_ROOT}}/**`，`INSTALL.md` §1/§2.2/§3/§6 同步该要求。
- **B2 机器层红线**：机器层补回 `*.env` / `~/.ssh` deny + bash 红线（与 `share/opencode.json` 同款），未挂载项目（如 `D:\qb`）同样生效。
- **B3 死重清理（结论修正）**：机器层 `package.json` / `package-lock.json` / `node_modules` / `.gitignore` 经重启验证由 opencode 启动时**自动重建**（插件 SDK 依赖，属运行时管理产物，非死重）；仅 `bun.lock` 未重建。`_trash-20260914/` 已删除。
- **A1 复核**：`share/tools/kb.py` 凭据读取机器层 `~/.config/opencode/kanboard.env`，实测 `open` / `log` 正常（无 401）；无需改代码。
- 回滚：机器层还原 `opencode.json.bak-20260914`；仓库 `git revert` 对应提交。