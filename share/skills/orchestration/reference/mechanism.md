# 编码编排机制（开发组：leader / coder / tester / reviewer）

> 本文件是**机制通用版**（与具体项目/机器无关）。实例（sprint 文件、决策记录、验收器等）留在各工作区的编排目录（默认 `<工作区>/orchestration/`，路径由工作区 `AGENTS.md` 声明）。
> 分层：机制 = 本文件 + 模板（`reference/`）；实例 = 工作区编排目录。二者分离，新环境按 `deployment.md` 部署。
> 承载：产品代码在产品仓库（`<产品仓库根>`）；编排实例目录**独立于产品仓库**，自成一个本地 git 仓库（无 remote），见 §6/§11。

## 1. 角色

| 角色 | agent | mode | 职责 | 写权限 |
|---|---|---|---|---|
| leader | `leader` | primary | 拆卡、派发、仲裁、质量门、合并提交、写决策 | 只写编排目录与机械性小修（≤10 行，须记录） |
| coder | `coder` | subagent | 按单张任务卡实现 + 单测 | 任务卡写范围内 |
| tester | `tester` | subagent | 独立复跑验收、集成/契约用例、批次回归、出证据 | 测试资产目录（约定） |
| reviewer | `reviewer` | subagent | 只读审计 diff + 输出测试缺口清单 | 无 |
| tester-alt | `tester-alt` | subagent | sprint 收尾机器验收复核（验收器报告 + 对抗抽检 + 人工项核对，异模型） | 默认只读为主 |
| reviewer-alt | `reviewer-alt` | subagent | 高风险 sprint 终审走查（异模型） | 无 |
| scout | `explore`（内置） | subagent | 只读调研 | 无 |
| watchdog | `watchdog` | primary | 编排链看门狗：低频检查 sprint 闭合/卡死，异常 `notify_parent` + 看板留痕；文件自证退出 | 无（只读 + 通知/看板评论） |

- **模型分层**：实现与验收模型不同源（任务级用常规实现模型；sprint 验收复核用替代模型），降低同构盲区。agent 文件的 `model` 字段独立配置。
- 权限原则：用 allow/deny 表达（危险命令直接 deny），不用 ask，避免无人值守被弹窗中断。
- 边界：开发组只管实现；需求口径由产品/需求角色维护，遇缺口记录并回报。

## 2. 任务卡（原子任务书）

- 模板：`reference/task-card-template.md`（实例可存一份可定制副本）。
- 字段：ID / spec 引用 / 写范围 glob / 接口冻结项 / 验收命令+期望 / DoD / 停止条件 / 模型档 / 依赖。
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
6. 未提交并行改动的干扰：tester 模块级复跑为主；全量回归在批次提交后。

## 4. 决策与不中断策略

决策阶梯（逐级下探，全部写 `decisions.md`）：

1. spec / 契约有明文 → 直接执行；
2. 仓库有先例 → 沿用；
3. 可逆技术选择 → leader 定；
4. 影响接口/范围但可逆 → 最小变更 + TODO，继续，批次报告提示人工复核；
5. 硬停清单 → 停该任务、记录、继续独立任务，批次末汇总。

硬停清单（不可逆/高危）：删数据或破坏性迁移、支付金额/退款口径、密钥与真实外部调用、破坏已冻结契约、超出既定范围。**硬停 = 不执行并上报，不是等人确认。**

失败阶梯：执行者自修 ≤2 → leader 换方案/补卡重派（**同一任务重派上限 2 次**）→ 仍不成标 `blocked`、强制人工 → 批次末清单。

## 5. 质量门

- 任务门：卡内验收命令 + 项目静态检查 + 相关测试；reviewer 只读审 diff（对 spec，不对自述）；tester 独立复跑（证据 = 原始输出）。
- 防自证：测试基于 spec；执行者自测只算回归资产、不算验收证据；reviewer 输出测试缺口 / 对抗用例清单。
- 批次门 = **机器验收**（`<编排目录>/tools/acceptance.py`，退出码判定；报告 `runs/<S>-acceptance.md`）：项目静态门 + 分层测试 + 迁移升降（隔离库）+ 产品仓库 `git status` 干净 + 敏感文件扫描 + 证据文件完整性；由 `tester-alt`（异模型）复核报告与 `[人工]` 项清单。**命令清单事实源 = 项目命令区 + 验收器实现，改门禁须同步。**
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
| `tools/acceptance.py` | 批次门机器验收器（骨架见 `reference/acceptance-skeleton.py`） | 人工维护 |
| `templates/` | 任务卡 / sprint / milestone / 链会话模板（可定制副本；通用版见 `reference/`） | 人工维护 |

- 编排目录 = **独立本地 git 仓库**（无 remote）；产物提交到该仓库，不进产品仓库。
- 产品代码提交在**产品仓库**（unaffected）。

## 7. 启动方式

1. **派发 leader 会话（推荐）**：主会话 `spawn_session({ agent: "leader", title: "[<S>] <名称> · sprint", prompt: <开场指令> })`；手动等价 `@spawn --agent leader --title "<标题>" <开场指令>`。派发后主会话可继续规划（不阻塞）。
2. 备选：Tab 切到 `leader` agent（会话起点 = 工作区根；agent 在工作区 `.opencode/agent/` 加载）；口令「开发组」即指本团队。需人工逐步交互时用此方式。
3. 开场指令模板：`按 <编排目录>/README.md 与机制全文执行 <目标>；输入：<任务书路径 或 FR/design 引用>；默认全自动，硬停项记入 decisions.md 并继续。`
4. 需要先审计划时，加一句 `仅出 sprint 计划与任务卡，不开跑`。

## 8. 与任务书 / 看板的关系（可选接入）

- 选择标准：环境 / 一次性 / 跨工具接力 → 任务书（单会话直执行）；多任务、需要并行与审查 / 测试分工 → sprint 编排。同一工作项只走一套机制，不混用。
- 任务书：环境类 / 一次性 / 跨工具接力照旧；其「执行步骤/验收」可作为 leader 拆卡输入。
- 看板（可选，如 Kanboard；对外唯一状态源，列：`待办 / 预备 / 进行中 / 待验收 / 完成`）：
  - 卡 = 工作项；sprint 内任务卡不上板。同步只在边界写：sprint 开工（卡 → 进行中 + 评论载体路径）与收尾。
  - 收尾规则：**机器验收 PASS 且无 `[人工]` 项 → 卡直接移「完成」+ 评论（报告路径 / 提交哈希）**；有 `[人工]` 项 → 「待验收」+ 只列人工项；返工由人定。
  - 执行中机器状态以 `sprints/<S>.md` 为准，不逐任务刷板。

## 9. 进入 leader 的时机（两阶段开跑）

前提（缺一不进）：设计/机制定稿；目标明确且口径冻结；输入引用齐备；上一阶段（milestone）已 accepted。

流程：

1. **Plan 预演（人工在场）**：确认目标、输入引用、范围、并行组、硬停项、验收口径；产出"已对齐的目标与约束"（拆卡留给 leader）。
2. **进入 leader**：默认**派发新会话**（`spawn_session({ agent: "leader", ... })`，把 Plan 结论写进开场指令）；需人工在场时 Tab 切 leader。
3. **首轮保险（可选）**：先发「仅出 sprint 计划与任务卡，不开跑」，人工扫并行组与写范围后回「开跑」。
4. **全自动**：leader 拆卡 → 派发 → 门禁 → 逐任务提交；人只处理硬停项。
5. 稳定 1–2 个 sprint 后可跳过 Plan 预演。

不进 leader：机制仍草案、口径未决、需改契约、超出既定范围。

## 10. 审查轮（reviewer 协议）

reviewer = 只读文档式审查：对 diff 与 spec，不运行代码（执行归 tester）。输出含：复述理解、分级发现（blocker / major / minor / nit，`file:line` + spec 依据）、待答复问题、测试缺口清单。

轮次规则：

1. **常规任务**：一轮审查。无 blocker 即过门；major / minor / nit 由 leader 决定修或记 TODO。
2. **高风险 / blocker 任务**（契约变更、支付、鉴权、数据迁移、跨模块接口）：两轮走查——① reviewer 出发现 + 问题清单 → ② leader 中转给 coder 答复 / 修复 → ③ reviewer 复检（只对 blocker 与答复项）。
3. **多视角（可选）**：leader 按风险并行派 2–3 个 reviewer，各限定视角（安全 / 数据一致性 / 规范），结果由 leader 合并；默认单 reviewer。
4. 成本纪律：走查轮与多视角只对高风险任务启用。
5. 跨模型：sprint 验收复核由 `tester-alt`（替代模型）执行；高风险 sprint 可加派 `reviewer-alt` 终审走查。

## 11. 连续性与分支

- **状态事实源**：`sprints/<S>.md` 是 sprint 唯一状态源；leader 每派发 / 完成 / 阻塞一个任务即更新（状态、在途标记、最后动作、下一步）。
- **双仓库**：产品代码与分支在产品仓库；编排实例（sprint/decisions/runs/milestones）在**独立编排仓库**。代码提交信息带任务号 `[T-xx]`；编排产物提交到编排仓库（`git -C <编排目录> …`）。
- **恢复协议**：leader 会话中断 / compaction 后，新 leader 读 `sprints/<S>.md` → `runs/` → 产品仓库 `git log`，按「在途任务」标记判定：未提交的丢弃重派、已提交未过门的补验、其余按 DAG 续跑；恢复动作写 `decisions.md`。
- **分支策略**：一个 sprint 一条分支 `sprint/<S>`（产品仓库）；leader 在分支上逐任务提交，批次门全绿后合并回 main（不 push）；批次失败则分支保留、不合并。任务书类执行照旧直接提交 main。
- **回滚**：任务失败 = 丢弃未提交改动或 `git revert` 该任务 commit（产品仓库）；编排产物在编排仓库回滚。

## 12. 反馈与收尾

- **中间报告**：每完成 N 个任务（默认 3）或每 30 分钟，leader 在会话输出 ≤10 行进度摘要（完成 / 阻塞 / 花费），不阻塞执行。
- **验收清单（分层）**：sprint 收尾 leader 产出验收清单，逐项标 `[机器]`（引用 `runs/<S>-acceptance.md`）与 `[人工]`（视觉 / 产品口径 / 真机生态 / 高危授权，给可复现步骤）。**机器 PASS 且 `[人工]` 为空 → 自动 accepted**；有 `[人工]` 项 → 待人工终审；返工移「预备」+ 评论。
- **Milestone 闭合检查（§14）**：sprint 收尾时若本 sprint 关闭所属 milestone 的最后一项 → 生成验收包、状态置 `awaiting-human`、**停止，不派下一阶段 sprint**。
- **预算熔断**：可选；如需成本审计再议。

## 13. 会话派发与串行约束

- **派发通道**（`opencode-session-spawn` 插件）：
  - 自动：主会话 `spawn_session({ agent: "leader", title, prompt })`；手动：`@spawn --agent leader --title "<标题>" <开场指令>`。
  - 落点：默认继承当前工作目录；跨目录派发显式传 `directory`。
  - 标题约定：`[<S>] <名称> · sprint`。
- **串行硬规则**：同一工作树同一时刻最多 **1 个未关闭 sprint**（避免 git 工作树、测试库、端口、main 合并互踩）。派发前检查：`<编排目录>/sprints/` 无 doing / 未关闭，且看板无「进行中」卡。上一 milestone 未 accepted 前不得派发下一阶段 sprint（§14）。
- **登记**：派发后主会话在 `sprints/<S>.md` 头部记「派发会话标题 / 时间」；看板卡 → 进行中（可选）。
- **回收**：spawn 为 fire-and-forget、无回调；主会话 / 人按需轮询 `sprints/<S>.md` + `runs/` + 看板取结果；`[人工]` 项由人处理（§12）。
- **事件驱动通知**（`opencode-session-spawn` 插件）：子会话可用 `notify_parent({ text })` 向**父会话**（spawn 者）注入 `[relay] <text>` 并唤醒；仅父会话、无重试 / 追踪；**防环：收到 `[relay]` 一律不自动回发**。
- **UI 已知行为**：桌面端 composer 模式选择器不读取会话 `agent`，被派发会话在 UI 显示默认模式；但注入的首条消息以指定 agent 执行；无人值守流程不受影响。**人工介入前需在 UI 手动切到 Leader 模式。**
- **链：B 主 + A 兜底**（协议与开场模板 `reference/chain-session-template.md`）：
  - **B 主（快路径）**：链会话 = **棒级**调度者，由主会话一次性 spawn（建议显式 `model`）；链会话 spawn 本棒 leader 与 watchdog（`notify_parent` 落点 = spawn 者 = 链）；收到 `[relay]` → 只读校验（`sprints/<S>.md` 闭合 + `runs/<S>-acceptance.md` + 产品仓库合并提交 + 工作树干净）→ 派下一棒 / milestone 收尾上报主会话；空闲待命、不轮询、不自动回发。链会话 id 记入 `runs/chain.md`。
  - **A 兜底（看门）**：`watchdog` agent 每棒一个独立会话，低频（默认 30min / ≤8 轮 / 收尾 15min / 卡死 90min，阈值可由起始语句覆盖）；异常 → `notify_parent` 链 + 看板评论；**文件自证退出**。
  - **主会话零打扰**：主会话只启动链一次；除 milestone 收尾单条 `[relay]` 外不收任何通知。

## 14. Milestone 阶段验收门

- **定义**：milestone = 一个业务阶段，是若干 sprint / 工作项（卡）的集合；载体 `milestones/<M>.md`（范围表 + 机读块 + 验收包），索引 `milestones/README.md`，模板 `reference/milestone-template.md`。
- **状态机**（映射看板列）：`planned（预备）→ doing（进行中）→ awaiting-human（待验收）→ accepted（完成）/ rejected（返工 → doing）`。
- **触发（闭合检查）**：leader 在 sprint 收尾时核对所属 milestone 范围——全部工作项 done/accepted、各 sprint 文件状态 `done`、`runs/<S>-acceptance.md` 全 PASS（验收器引入前的历史 sprint 走机读块 `machine_report_exempt` 显式豁免）、产品仓库 git 干净 → 生成验收包、状态置 `awaiting-human`、**停止，不派下一阶段 sprint**；milestone 最后一项是任务书（非 sprint）时，由主会话执行同一检查。
- **验收包内容**：① 范围与载体表；② 机器汇总（各 sprint 报告 + 产品仓库封印复跑 `python <编排目录>/tools/acceptance.py --milestone <M>`，报告 `runs/<M>-milestone-acceptance.md`）；③ 跨 sprint `[人工]` 汇总（去重 + 可复现步骤）；④ 阶段目标核对；⑤ 整体验证命令；⑥ 遗留 / 债务；⑦ 下一阶段入口确认；⑧ 人工结论区。
- **闸门语义**：milestone 未 accepted 前不得派发下一 milestone 的编排 sprint；返工 / 收口 sprint 与独立任务书不受限。
- **人工结论必填**（机制本体，不允许全自动）；零 `[人工]` 项时允许快速确认。
- **跑封印复跑前先把 `milestones/<M>.md` 提交到编排实例仓库**（保证封印快照可追溯）；相关文档同步后再复跑。
- **看板同步（可选）**：阶段卡只在边界写——包就绪 → 「待验收」+ 评论；人工结论 → 「完成」/ 返工。
