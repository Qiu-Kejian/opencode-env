---
name: orchestration
description: 编码编排机制（开发组 leader / coder / tester / reviewer / -alt 异模型复核）：单会话内多 agent 并行编码的任务卡拆分、质量门、决策留痕与阶段验收。Use when 用户说「开发组」「编排」「sprint」，或要按 leader/coder/tester/reviewer 机制派发与验收编码任务。触发词：开发组、编排、sprint、leader、质量门、验收复核。
---

# 编码编排（开发组机制 · 通用版）

> 本 skill 是**机制模板**。分层：机制全文见 `reference/mechanism.md`；实例（sprint 文件、决策记录、验收器等）留在各**工作区**编排目录（默认 `<工作区>/orchestration/`，路径由工作区 `AGENTS.md` 声明）。
> 实例目录**独立于产品仓库**，自成一个本地 git 仓库（无 remote）；新环境部署见 `reference/deployment.md`。

## 参考文件

| 文件 | 用途 |
|---|---|
| `reference/mechanism.md` | 机制全文（§1–§14）：角色 / 任务卡 / 并行 / 决策 / 质量门 / 目录 / 启动 / 链 / milestone |
| `reference/deployment.md` | 新环境部署指南（锚点定义 → 实例目录 + git → 模板 → 声明 → 验收器 → 冒烟） |
| `reference/task-card-template.md` | 任务卡模板 |
| `reference/sprint-plan-template.md` | sprint 计划模板 |
| `reference/milestone-template.md` | milestone 验收包模板 |
| `reference/chain-session-template.md` | 链会话（B 主 + A 兜底）模板 |
| `reference/acceptance-skeleton.py` | 批次门验收器骨架（双根 ORCH/REPO、退出码、报告） |

## 1. 角色（agent 定义在 `.opencode/agent/`）

| 角色 | agent | mode | 职责 | 写权限 |
|---|---|---|---|---|
| leader | `leader` | primary | 拆卡、派发、仲裁、质量门、合并提交、写决策 | 只写编排目录与机械性小修（≤10 行，须记录） |
| coder | `coder` | subagent | 按单张任务卡实现 + 单测 | 任务卡写范围内 |
| tester | `tester` | subagent | 独立复跑验收、集成/契约用例、批次回归、出证据 | 测试资产目录（约定） |
| reviewer | `reviewer` | subagent | 只读审计 diff + 输出测试缺口清单 | 无 |
| tester-alt | `tester-alt` | subagent | sprint 收尾机器验收复核（验收器报告 + 对抗抽检 + 人工项核对，异模型） | 默认只读为主 |
| reviewer-alt | `reviewer-alt` | subagent | 高风险 sprint 终审走查（异模型） | 无 |
| scout | `explore`（内置） | subagent | 只读调研 | 无 |
| watchdog | `watchdog` | primary | 编排链看门狗：低频检查 sprint 闭合/卡死，异常 `notify_parent` + 看板留痕；文件自证退出 | 无 |

- **模型分层**：实现与验收模型不同源（任务级用常规实现模型；sprint 验收复核用替代模型），降低同构盲区。
- 权限原则：用 allow/deny 表达（危险命令直接 deny），不用 ask，避免无人值守被弹窗中断。
- 边界：开发组只管实现；需求口径由产品/需求角色维护，遇缺口记录并回报。

## 2. 任务卡（原子任务书）

- 模板见 `reference/task-card-template.md`：ID / spec 引用 / 写范围 glob / 接口冻结项 / 验收命令+期望 / DoD / 停止条件 / 模型档 / 依赖。
- 粒度：单任务 1–3 个文件组；验收可复制执行；写范围白名单外零改动。
- 拆分原则：默认**垂直切片**；契约 / 模型 / schema 类水平先行；不按文件拆。
- 拆卡自检：写范围两两不相交；验收命令可复制；必读精确到节；依赖无环。
- 派发时任务卡**全文**进 subagent prompt（冷启动）。

## 3. 并行规则

1. 可并行 = 写范围不相交 且 不涉及共享接口变更。
2. 契约先行：契约类任务先串行冻结，再 fan-out。
3. 默认文件级分区；高冲突风险用 git worktree 隔离，leader 合并。
4. 并发上限 2–3；每任务一个 commit（`<type>(<scope>): <摘要> [T-xx]`，产品仓库），leader 统一提交，不 push。
5. 测试库 / 端口隔离；并行任务间不得存在 import / 接口耦合。

## 4. 决策与不中断策略

决策阶梯（逐级下探，全部留痕）：
1. spec / 契约有明文 → 直接执行；
2. 仓库有先例 → 沿用；
3. 可逆技术选择 → leader 定；
4. 影响接口/范围但可逆 → 最小变更 + TODO，继续，批次报告提示人工复核；
5. 硬停清单 → 停该任务、记录、继续独立任务，批次末汇总。

硬停清单（不可逆/高危）：删数据或破坏性迁移、支付金额/退款口径、密钥与真实外部调用、破坏已冻结契约、超出既定范围。**硬停 = 不执行并上报，不是等人确认。**

失败阶梯：执行者自修 ≤2 → leader 换方案/补卡重派（同一任务重派上限 2 次）→ 仍不成标 `blocked`、强制人工 → 批次末清单。

## 5. 质量门

- 任务门：卡内验收命令 + 项目静态检查 + 相关测试；reviewer 只读审 diff（对 spec，不对自述）；tester 独立复跑（证据 = 原始输出）。
- 防自证：测试基于 spec；执行者自测只算回归资产、不算验收证据；reviewer 输出测试缺口 / 对抗用例清单。
- 批次门 = **机器验收**（`<编排目录>/tools/acceptance.py`，退出码判定，报告 `runs/<S>-acceptance.md`）：项目静态门 + 分层测试 + 迁移升降（隔离库）+ 产品仓库 `git status` 干净 + 敏感文件扫描 + 证据文件完整性；由 `tester-alt`（异模型）复核报告与 `[人工]` 项。骨架见 `reference/acceptance-skeleton.py`。
- flaky 政策：禁止"重跑直到绿"；门禁以**首次结果**为准；发现 flaky → 记录 + 隔离标记 + 建修复任务。

## 6. 产物与目录（实例）

| 路径 | 内容 | 写入者 |
|---|---|---|
| `README.md` | 实例薄文档：工作区/产品仓库锚点、命令区指向、看板、端口 | 人工维护 |
| `sprints/<S>.md` | 状态事实源：任务 DAG + 状态 + 在途标记 + 冻结区 + 恢复指引 + 结束报告 | leader |
| `decisions.md` | append-only 决策记录 | leader |
| `runs/<task-id>.md` | 任务证据：命令原始输出、diff stat、评审结论 | leader 落盘 |
| `runs/<S>-acceptance.md` | 机器验收报告 | 脚本生成 |
| `milestones/<M>.md` | 阶段验收包 + 人工结论；索引 `milestones/README.md` | leader / 主会话 |
| `tools/acceptance.py` | 批次门机器验收器 | 人工维护 |
| `templates/` | 任务卡 / sprint / milestone / 链会话模板（可定制副本） | 人工维护 |

- 编排目录 = **独立本地 git 仓库**（无 remote）；产物提交到该仓库；产品代码提交在产品仓库。

## 7. 启动方式

1. **派发 leader 会话（推荐）**：主会话 `spawn_session({ agent: "leader", title: "[<S>] <名称> · sprint", prompt: <开场指令> })`；手动等价 `@spawn --agent leader --title "<标题>" <开场指令>`。
2. 备选：Tab 切到 `leader`；口令「开发组」即指本团队。
3. 开场指令模板：`按 <编排目录>/README.md 与机制全文执行 <目标>；输入：<任务书路径 或 FR/design 引用>；默认全自动，硬停项记入 decisions.md 并继续。`
4. 需要先审计划：加一句 `仅出 sprint 计划与任务卡，不开跑`。

## 8. 边界同步与看板（可选接入）

- 对外状态源（如 Kanboard）只在边界写：sprint 开工 → 卡「进行中」；收尾 → 机器 PASS 且无 `[人工]` 项 → 「完成」，否则「待验收」；返工 → 「预备」。
- 执行中状态以 `sprints/<S>.md` 为准，不逐任务刷板。

## 9. 进入 leader 的时机

前提（缺一不进）：设计/机制定稿；目标明确且口径冻结；输入引用齐备；上一阶段（milestone）已 accepted。
不进 leader：机制仍草案、口径未决、需改契约、超出既定范围。

## 10. 审查轮与连续性

- 常规任务一轮 review；高风险任务两轮（发现 → 答复/修复 → 复检）；多视角按风险可选。
- 状态事实源 = `sprints/<S>.md`；中断恢复：读 sprint 文件 → `runs/` → 产品仓库 `git log`，按在途标记判定续跑，恢复动作留痕。
- 分支：一 sprint 一分支（产品仓库），batch 门全绿合并回 main（不 push）；失败分支保留。
- 收尾：验收清单分层标 `[机器]` / `[人工]`；机器全 PASS 且无 `[人工]` → 自动 accepted；阶段关闭时生成 milestone 验收包并**停止**下一阶段派发。

## 11. 会话派发与串行约束

- 同一工作树同一时刻最多 1 个未关闭 sprint；派发前检查 `<编排目录>/sprints/` 无进行中、看板无「进行中」卡。
- 派发后登记；回收靠轮询 sprint 文件 + 证据目录 + 看板（spawn 无回调）。
- 双仓库：编排产物提交到编排仓库（`git -C <编排目录> …`）；代码提交在产品仓库。
