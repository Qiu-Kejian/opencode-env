# 链会话模板（B 主 + A 兜底）

- 用途：主会话**一次性**启动编排链时，按本模板生成链会话起始语句；链协议全文见 `mechanism.md` §13 与本文。
- 角色：链会话 = 编排链的调度者（**棒级**）；mode 默认（build）、目录 = 工作区根；不做实现、不审计、不写产品代码。
- 拓扑（通知落点 = spawn 者）：链会话 = 每棒唯一 spawner（leader 与 watchdog 的 `notify_parent` 落点）；主会话只启动链一次，此后零打扰（唯一例外：milestone 收尾一条）。

## 主会话启动（一次性）

1. `spawn_session({ title: "[链] <M> 编排链", model: "<实现模型>", prompt: <开场指令> })`
   - **建议显式 `model`**（若本机无默认模型）；`agent` 用默认（build）即可。
   - `select` 用默认（桌面端为 no-op；TUI 下不想抢焦点可显式 `select: false`）。
2. 把链会话 id 记入 `<编排目录>/runs/chain.md`（不存在则创建；人工定位用）。
3. 之后主会话不介入；milestone 收尾时会收到链的一条 `[relay]`。

## 开场指令（模板）

> 你是 <M> 编排链的链会话（协议：`mechanism.md` §13 + `chain-session-template.md`）。
> 本链棒清单：<S1、S2、…>；首棒：<S1>（输入：<任务书路径 / FR / design 引用>）；milestone：<M>。
> 动作：① 校验无未关闭 sprint；② 写 `sprints/<S1>.md` 登记并提交到编排实例仓库；③ `spawn_session` 首棒 leader（`agent: "leader"`，模型由 agent 固定）+ 首棒 watchdog（`agent: "watchdog"`，起始语句见下）；④ 空闲待命，只等 `[relay]`，不轮询、不睡眠。
> 收到 `[relay]` 按「通知处理协议」判定；**不自动回发通知**。

## watchdog 起始语句（模板）

> 你是 <S> 的 watchdog（协议：`watchdog` agent）。本棒 sprint：<S>；下一棒：<S+1，或"milestone 收尾，无下一棒">；milestone：<M>；间隔：<30min>；轮数上限：<8>；阈值：收尾 <15min> / 卡死 <90min>。

## 通知处理协议（收到 `[relay]` 后，按序）

1. 解析通知里的 sprint 名（缺省 = 当前棒）。
2. 只读校验：`sprints/<S>.md` 状态（done/accepted）+ `runs/<S>-acceptance.md` 存在 + 产品仓库 `git log` 已含合并 main 提交 + 工作树干净。
3. 判定：
   - **闭合且还有下一棒** → 写下一棒 `sprints/<S+1>.md` 登记 + 提交到编排实例仓库 → `spawn_session` 下一棒 leader + 新 watchdog → 一句话回报（不回发通知）。
   - **闭合且 milestone 收尾** → 不派发；`notify_parent("[chain] <M> 收尾待人工（awaiting-human）")` 向主会话发**一条**；输出提示等人工（milestone 门，`mechanism.md` §14）。
   - **未闭合（watchdog 告警）** → 不动作（记录；等下次通知/人工）。
   - **条件不满足/文件缺失** → 不动作（防误派），必要时输出原因。
4. 防环：收到 `[relay]` 一律**不自动回发**通知；只做「向前推进」。

## 失败/降级

- 链不做重试；`notify_parent` 失败（链会话被关/异常）→ 退回**看板评论 + sprint 文件**留痕（人工/主会话主动查看可恢复）。
- 仓库内文档更新只在无在跑 sprint 时做。
- A 手动兜底保留：人可随时手动补派/接管；链与 watchdog 任一失效，sprint 本身不受影响（状态在文件）。
