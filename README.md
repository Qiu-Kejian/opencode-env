# opencode-env

opencode 公共配置环境仓库（agents / skills / AGENTS.md 等），跨项目、跨机器共享。

- 仓库根：本文档 + 工作区工具文件
- `share/`：**真正的配置挂载层**（agents/、skills/、AGENTS.md）——各项目根用目录联接（junction）挂到 `.opencode` 时，指向的是 `share/`
- 目的：把「多项目共享的公共配置」从各项目目录里抽出来，单一 git 来源，远程同步，多机迁移

## 为什么拆两层（README 与挂载内容分离）

junction 是目录级链接——若项目根 `.opencode` 直接指向仓库根，仓库根里的 `README.md` 等文件会透过 `.opencode\` 出现在项目根文件树中。

因此仓库拆 **仓库根（文档/工作区）** 与 **`share/`（挂载内容）** 两层：

```
E:\oce\opencode-env\          ← git 仓库（README 在这里，人可打开看）
├── README.md                 ← 本文档（不进入任何项目根）
├── .gitignore
└── share\                    ← 挂载层（junction 目标在这里）
    ├── AGENTS.md             ← 公共规则
    ├── agents\               ← 公共 agent 定义
    └── skills\               ← 公共技能
```

项目根 `.opencode` → junction → `E:\oce\opencode-env\share`，README 完全不可见。

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

opencode 的规则与配置按作用域分层，全部 **merge（deep merge）+ instructions 拼接（concat + Set 去重）**，非覆盖：

```
┌─ ① 全局层      ~/.config/opencode/          ← 个人/机器全局（不随仓库走）
├─ ② 公共层      项目根上一级 .opencode        ← 本仓库（junction 挂载），多项目共享
├─ ③ 项目层      项目根 .opencode              ← 本项目真实目录，自定义 agents/skills
├─ ④ 深度层      各 git 代码仓库内 AGENTS.md   ← 与代码同源，随仓库版本控制
└─ ⑤ 世界层      ~/.claude/CLAUDE.md 等(兼容)
```

加载顺序从高层到低层：全局 → 公共 → 项目 →（向下不自动扫）各代码仓库内的 AGENTS.md 不会被自动索引，只有 `instructions` glob 显式引入才进上下文。

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
git clone <remote> E:\oce\opencode-env

# 项目根挂载 .opencode
mklink /J "E:\idcas\08\.opencode" "E:\oce\opencode-env\share"
Remove-Item "E:\idcas\08\.opencode"            # 若已存在真实目录先删除
```

跨平台注意：junction 是 NTFS 特性；macOS/Linux 用 `ln -s`（symlink），仓库结构不变、挂载方式不同。

## 与 OPENCODE_CONFIG_DIR 对比

| 方式 | 选择性挂载 | `.opencode/...` 相对引用 | 受 worktree 边界影响 | 官方机制 |
|------|:---:|:---:|:---:|:---:|
| junction（本仓库方案） | ✅ 按项目控制 | ✅ 全链路可用 | ⚠️ git-root 项目断链 | 系统级，非 opencode 概念 |
| `OPENCODE_CONFIG_DIR` env | ❌ 全局生效 | ❌ 需改引用 | ❌ 不受影响 | ✅ 官方一等公民 |

`OPENCODE_CONFIG_DIR` 指向仓库根时，opencode 像扫 `.opencode` 一样扫描它，且加载顺序在项目 `.opencode` 之后（可覆盖），作为第四个 sources 无条件生效。缺点是对所有项目生效、且在 `directories` 中排最后。

## 技能审计清单（TODO：逐项审计后入 share/）

以下内容当前在 `E:\dev\.opencode`，**尚未审计入仓**，逐项评估后移入 `share/`：

- [ ] `agents/`：assistant / coder / coder-pro / lead / planner / reviewer / tester / uidesigner（8 个 .md）
- [ ] `skills/`：browser-automation / create-project-from-requirement / daily-review / de-aiify / import-zentao / inbox-processor / kefu-demand-flow / mockoon-config-gen / morning-plan / prep-meeting / process-meeting / research-assistant / sync-gtd-status / sync-smart-service / test-env-prep / thinking-partner / ui-designer / update-zentao-data / weekly-synthesis / weekly-zentao-report / work-handoff / yxxg-assign-dev（22 个）
- [ ] `AGENTS.md`：公共规则是否入 `share/`
- [ ] `commands/`：尚无，目录预留
- [ ] ⚠️ 待审要点：skills 内硬编码绝对路径（`E:\dev\...` 等）在迁移后是否失效，需逐项核对或改造为相对引用

审计完成后更新本文档与 git 提交。