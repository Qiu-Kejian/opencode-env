# INSTALL · 新环境引导安装

> 用途：在**新机器 / 新项目**上把 opencode 公共配置层装起来（junction 挂载 + 本机参数具体化）。
> 执行主体：opencode 会话（人工阅读亦可）。
> 触发话术：克隆本仓库后，在本目录启动 opencode，说：「**读 INSTALL.md 并执行安装**」。
> 原则：`share/` 是跨机共享内容，**安装过程不修改 share**；本机值写机器层，项目值写项目层。

## 0. 前置检查

```powershell
git --version; opencode --version
Test-Path .\share\AGENTS.md   # 必须在仓库根执行；返回 True 才继续
```

- 平台：Windows 用 **junction**（`mklink /J`，无需管理员）；macOS / Linux 用 **symlink**（`ln -s`），下文命令给出两种写法。
- 安装全程遵循：先问参数（不猜）→ 先备份（不覆盖）→ 每步验证。

## 1. 参数收集（先问，不猜）

用 question 工具逐项与用户确认，得到一张参数表：

| 参数 | 说明 | 示例 |
|---|---|---|
| `<repo-root>` | 本仓库克隆的绝对路径（同时写入机器层 `external_directory` 白名单，见 §2.2） | `E:\oce\opencode-env` |
| `<home>` | 用户主目录 | `C:\Users\xxx` |
| `<项目根清单>` | 要挂载的工作区根（会话起点；**注意不是 git 仓库内的子目录**） | `D:\dev\bbcare` |
| 可选组件 | DBX / Mockoon / Pen design / Kanboard 看板（依赖 WSL 或容器 + 凭据，见 §5）/ Ollama 本地模型 | 按需勾选 |
| 模型可用性 | agent 中声明的模型（默认 `deepseek/deepseek-v4-flash`、`opencode/big-pickle`）在本账号是否可用 | 可用 / 需替换 |
| 凭据 | 是否本机重建 `kanboard.env` 等（值不落库、只落机器层） | 是 / 否 |

## 2. 机器层生成（不入库）

机器层 = `~/.config/opencode/`（全局配置目录），承载本机差异：

1. **备份已有配置**（存在才做）：
   ```powershell
   robocopy "<home>\.config\opencode" "<home>\.config\opencode.backup-$(Get-Date -Format yyyyMMdd)" /E
   ```
2. **生成 `opencode.json`**：以 `install/machine.opencode.json.template` 为底，替换占位符后**与已有配置合并**（保留未涉及字段；同名 `mcp` 条目按本机实际覆盖）。模板里每段都注明占位符含义与可选删除项。**必须包含 `external_directory` 的 `{{REPO_ROOT}}/**`（公共层仓库根）**——挂载项目会话经 junction 编辑 `.opencode/...` 时按真实路径判定，缺此条会触发 ask。
3. **生成 `AGENTS.md`（机器层个性化）**：记录本机环境——Python/解释器路径、预批准临时目录、模型可用性备注、MCP 简述、本仓库位置。示例：

   ```markdown
   # AGENTS.md（机器层 · 本机个性化，不入库）

   - Python：`python` 解析到 <本机解释器路径>（已装 xxx 依赖）
   - 预批准临时目录：<本机临时目录>
   - 模型可用性：<可用模型 / 不可用模型及替代>
   - 公共层仓库位置：<repo-root>（各项目 `.opencode` junction 指向其 `share/`）
   ```

4. **凭据（按需）**：`kanboard.env` 等只写机器层；从安全渠道重新签发，不从聊天/文档复制明文。

## 3. 泛化 → 具体化矩阵

`share/` 内是泛化内容；以下值**不得回写 share**，必须落到对应层：

| 泛化内容（share 层保持） | 具体化方式 | 落点 |
|---|---|---|
| 口令表中的默认目录/入口（taskbooks、orchestration） | 项目 `AGENTS.md` 声明实际路径 | 项目层 |
| agent 的权限路径（`.opencode/tools/*`） | 无需处理（相对引用，随 junction 成立） | — |
| agent 的模型名 | 本机不可用时用 `agent.<name>.model` 覆盖 | 项目根 `opencode.json` |
| 预批准临时目录、解释器路径 | 写入机器层 `AGENTS.md` | 机器层 |
| MCP（命令绝对路径、数据目录） | 模板替换后写入机器层 `opencode.json` | 机器层 |
| `external_directory` 白名单 | 本机实际项目盘/目录 + **公共层仓库根 `<repo-root>/**`**（junction 真实路径判定，见 §2.2） | 机器层 |
| 项目专属权限（如人读区 ask） | 项目根 `opencode.json`（宽规则在前、窄规则在后） | 项目层 |
| 凭据 | 机器层文件（不入库） | 机器层 |

## 4. 挂载（junction / symlink）

对 `<项目根清单>` 中每个项目根：

```powershell
# 先移除同名实体目录（存在才做；备份后再动）
# Windows（无需管理员）：
cmd /c mklink /J "<项目根>\.opencode" "<repo-root>\share"
# macOS / Linux：
ln -s "<repo-root>/share" "<项目根>/.opencode"
```

生成项目根 `opencode.json`（以 `install/project.opencode.json.template` 为底）：

- `instructions: [".opencode/AGENTS.md"]`（**必须**：`.opencode/AGENTS.md` 不会被自动发现，只能显式引入）
- 项目专属 `permission` 规则（可选）
- 项目根自己的 `AGENTS.md` 声明项目绑定：产品仓库根、事实源文档、taskbooks / orchestration 入口等（公共 agent 依赖此声明工作）

**自挂载本仓库**（否则在仓库内开会话将没有 skills/插件）：

```powershell
cmd /c mklink /J "<repo-root>\.opencode" "<repo-root>\share"
```

校验：`Get-Item "<路径>\.opencode" | Select LinkType,Target`（应为 Junction，Target = `<repo-root>\share`）；确认仓库根 `.gitignore` 已含 `.opencode/`（防止 junction 内容进 git）。

## 5. 依赖安装（按勾选）

| 组件 | 安装 / 验证 |
|---|---|
| Python（PDF/OCR 工具） | 装有 `pdf-inspector`、`pymupdf`、`rapidocr-onnxruntime`；验证 `python -c "import fitz, rapidocr_onnxruntime"` |
| Pen design（无头路线） | 安装 Pen CLI 并 `pen status` 通过；配置 `PEN_CLI_KEY`（用户级环境变量） |
| mermaid-render | `cd <repo-root>\share\tools\mermaid; npm install`；验证 `node ..\..\..\.opencode\tools\mermaid-render.mjs --help`（在挂载项目内） |
| Mockoon | `npm install -g @mockoon/cli@9.8.0`；验证 `mockoon-cli --version` |
| Playwright Chromium | `npx playwright install chromium`（mermaid 复用） |
| DBX / Pencil MCP | 安装对应应用/扩展，按机器层模板填命令路径 |
| Ollama（可选） | 安装 Ollama 并准备模板中声明的模型；验证 `ollama list` |
| officecli（可选） | 按其官方安装脚本，验证 `officecli --version` |
| Kanboard 看板（可选） | **启用**：按 `share/runbooks/kanboard-wsl.md` 部署/接入（新机先按 §8 核对重写该手册），机器层建 `kanboard.env`（凭据只落机器层）；验证 `python .opencode/tools/kb.py open`。**不启用**：跳过安装，并按 §5.1 禁用 pm-bot |
| 插件（codegraph / session-spawn） | 无需手工安装：opencode 首次启动自动从 npm 安装，缓存于 `~/.cache/opencode/packages/<包名>`；前提：首次启动可访问 npm registry；验证：重启后 `spawn_session` 等工具存在 |

### 5.1 组件禁用（未勾选的可选组件）

未勾选的可选组件除不安装外，还应关闭对应 agent/入口，避免 UI 与委派列表里出现必然失败的项。以 Kanboard 看板（pm-bot）为例：

- **机器级**（本机无看板、所有项目都不用）：在机器层 `opencode.json` 加
  ```json
  { "agent": { "pm-bot": { "disable": true } } }
  ```
- **项目级**（仅该项目不用看板）：在项目根 `opencode.json` 加同片段。

改配置后需**重启 opencode** 生效；重启后 pm-bot 不应出现在 Tab 切换与 task 委派列表中（验收见 §6）。

## 6. 验收（重启 opencode 后）

关闭并重启 opencode，在已挂载项目会话核对：

- [ ] agent：Tab 可见（如 leader / analyst / pen-designer），可派发（task）；pm-bot 仅在启用看板时可见/可派发
- [ ] skills：公共 skill 可被发现/路由（如 mockoon-env、db-designer）
- [ ] tools：`node .opencode/tools/mermaid-render.mjs --help`、`python .opencode/tools/kb.py`（如启用看板）可运行
- [ ] 组件选配：未启用看板 → Tab 与 task 委派列表均无 pm-bot；启用看板 → pm-bot 可派发且 `python .opencode/tools/kb.py open` 正常
- [ ] 权限：读 `*.env` 被 deny；项目声明的敏感目录（如 `.local/`）触发 ask
- [ ] 公共层访问：挂载项目会话对 `.opencode/` 下文件做一次 edit → 无 external_directory ask（`<repo-root>/**` 已在机器层白名单）
- [ ] MCP：机器层声明的 server 均可连接
- [ ] 插件：`share/opencode.json` 声明的 npm 插件已自动安装（`spawn_session` 等工具存在；`~/.cache/opencode/packages/` 下可见对应目录）
- [ ] 口令：公共口令表（`执行任务书` / `开发组` / `产品` / `美工` / `mermaid`）指向正确入口

## 7. 升级与回滚

- **升级**：`git pull`（本仓库）→ 所有挂载项目即时可见；涉及配置加载面的改动需重启 opencode。
- **回滚**：junction 用 `cmd /c rmdir "<路径>\.opencode"` 移除（只删链接、不触目标）；机器层配置从第 2 步备份恢复；重启 opencode。

## 8. 禁止项

- 不把本机/项目具体值写回 `share/`（准则见 `share/GOVERNANCE.md`）。
- 不提交任何密钥；凭据只落机器层。
- **新机先核对 `runbooks/` 再按手册操作**：runbooks 为「机器事实区」，内容随机器变化，旧手册可能完全失真。
- **无 WSL / 无看板的新机**：删除或替换不适用的 runbook（如 `kanboard-wsl.md`、`llm-pmbot.md`，以及与本机无关的项目手册），同步更新 `runbooks/README.md` 服务清单；不得保留标着「运行中」的失真记录。
- 不用 symlink/junction 指向仓库根（会让 README 等文件进入项目树）；挂载目标必须是 `share/`。
