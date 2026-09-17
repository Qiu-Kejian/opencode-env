# 编排机制部署指南（新环境）

> 目标：在一个新工作区把「开发组」编排机制跑起来。机制通用版见 `mechanism.md`；本文件只讲**怎么落地**。
> 占位：`<WS>` = 工作区根；`<REPO>` = 产品仓库根；`<ORCH>` = 编排实例目录（默认 `<WS>/orchestration`）。

## 0. 前置

- opencode 已装，且公共层可用：`.opencode/agent/`（leader / coder / tester / reviewer / tester-alt / reviewer-alt / watchdog）、`.opencode/skills/orchestration/`。
- 有可选接入项按需：session-spawn 插件（`spawn_session` / `notify_parent`）、看板（看板工具/凭据）、`git`。
- agent 权限以 allow/deny 表达（危险命令 deny），**不要用 ask**（无人值守会被弹窗中断）。

## 1. 定义锚点

在工作区 `AGENTS.md` 的「会话与 agent 约定」里写明：

- 工作区根 `<WS>`；产品仓库根 `<REPO>`（相对 `<WS>`）；命令区命令的工作目录 = `<REPO>`。
- 编排实例目录 `<ORCH>`（默认 `<WS>/orchestration`，**独立于产品仓库**，自成本地 git 仓库）。
- 任务书目录（可选，默认 `<WS>/taskbooks`）。
- 口令「开发组」入口 = `<ORCH>/README.md`。

> 规则：机制/实例的路径锚定**工作区根**；产品代码路径锚定**产品仓库根**。

## 2. 建实例目录 + 独立 git

```powershell
# 在 <WS> 下
New-Item -ItemType Directory -Path <ORCH>
git -C <ORCH> init
# 无 remote（不 push）
```

- `.gitignore`（实例内）：`__pycache__/`、`*.tmp`、本地临时文件。
- **可选**保留历史（从已入仓的旧实例迁移时）：`git -C <REPO> subtree split -P orchestration -b orch-split`，再把该分支取到新实例仓库。
- 目录骨架：`sprints/`、`runs/`、`milestones/`、`tools/`、`templates/`。

## 3. 从机制模板起实例

- 复制 `reference/task-card-template.md`、`sprint-plan-template.md`、`milestone-template.md`、`chain-session-template.md` 到 `<ORCH>/templates/`（按项目定制；通用版仍在 `reference/`）。
- 写 `<ORCH>/README.md`（**薄文档**）：工作区/产品仓库锚点、命令区指向（项目 `AGENTS.md`）、看板与端口、指向机制全文（`mechanism.md`）。**不要**把机制全文抄一遍。
- `milestones/README.md` 作里程碑索引。

## 4. 声明与口令（工作区 AGENTS.md）

- 会话起点 = `<WS>`（加载工作区 agent 与 skill）。
- 「开发组」口令 → 切 `leader`，入口 `<ORCH>/README.md`。
- 说明双仓库语义：代码提交在产品仓库；编排产物提交到编排仓库（`git -C <ORCH>`）。

## 5. 实现批次门验收器

- 以 `reference/acceptance-skeleton.py` 为起点，落到 `<ORCH>/tools/acceptance.py`；
- 双根：`ORCH`（实例，默认脚本父目录的上一级）、`REPO`（产品仓库根，`--repo` / 环境变量 / 项目声明）。
- 检查项（按项目命令区裁剪）：静态检查 + 分层测试 + 迁移升降（隔离库）+ 产品仓库 `git status` 干净 + 敏感文件扫描 + `runs/<id>.md` 证据完整性。
- 契约：退出码 = 判定（0 全 PASS / 非 0 有 FAIL）；报告写 `runs/<S>-acceptance.md`，结论行含 `**PASS**` / `**FAIL**`（供 milestone 聚合解析）。
- 命令清单事实源 = 项目命令区 + 本脚本；改门禁须同步。

## 6. 链与看门（可选）

- session-spawn 插件提供 `spawn_session` / `notify_parent`；链协议见 `mechanism.md` §13 + `chain-session-template.md`。
- `watchdog` agent 每棒一个会话；阈值由起始语句给出。
- 看板（可选）接入：边界同步规则见 `mechanism.md` §8。

## 7. 冒烟验收（可复制）

1. 会话起点 = `<WS>`；读工作区 `AGENTS.md` 能定位 `<ORCH>` 与 `<REPO>`。
2. 口令「开发组」→ 能切到 `leader`；leader 能读到 `<ORCH>/README.md` 与 `mechanism.md`。
3. 首轮保险：发「仅出 sprint 计划与任务卡，不开跑」，人工能看懂并行组与写范围。
4. `python <ORCH>/tools/acceptance.py --help` 正常；对历史 sprint 做一次 dry 调用，确认 `ORCH` / `REPO` 解析与报告落点（`<ORCH>/runs/`）。
5. `git -C <ORCH> status` 干净；`git -C <REPO> status` 干净。

## 8. 常见坑

- **不要**把编排实例放回产品仓库（会与「项目实例不入仓」冲突，且污染门禁的 git 干净判定）。
- 路径别写死本机绝对路径；一律用「工作区根 / 产品仓库根」锚点。
- 权限别用 ask；产线里一次弹窗就断链。
- 验收器报告结论标记（`**PASS**` / `**FAIL**`）与 `milestones/<M>.md` 机读块是机读契约，改动须同步。
- 链与 watchdog 失效不影响推进：sprint 状态在文件里，可人工接管。
