---
name: dbx
description: >
  Query databases and message queues through DBX MCP. Use when the user asks to
  look up data, inspect table structure, write or run SQL, or peek kafka/redis —
  e.g. "查一下库", "看下 xxx 表结构", "跑个 SQL", "有哪些表". Load before making
  any dbx_* tool call so the resolution and safety rules are in effect.
---

# DBX 数据库查询 Skill

通过 DBX MCP（stdio，服务名 `dbx`）操作 DBX 桌面端里已配置的数据库/消息队列。
所有工具形如 `dbx_*`。若本会话的工具列表里没有 `dbx_*` 工具，说明 DBX MCP 未连接，
停下并向用户说明需要在 opencode 配置里启用 `dbx`、重启会话后再试。

## 连接解析优先级

大部分工具同时接受 `connection_id` / `connection_name` / `database`：

1. 先 `dbx_list_connections` 拿到连接名与端点（别凭记忆猜连接名）。
2. 调用时优先用 `connection_name`（可读性好）。同一连接名指向稳定 ID。
3. 无默认库的连接，先 `dbx_list_databases` 再在参数里带 `database`。
4. 表名/库名拿不准时，先 `dbx_list_tables` / `dbx_describe_table` 确认真实存在。

## 标准查库流程

```
1. dbx_list_connections                      发现有哪些连接（端点/类型/默认库）
2. dbx_list_tables (connection_name, database)  列出表/视图
3. dbx_get_schema_context (connection_name, tables:[...])  取紧凑表结构写 SQL
4. dbx_execute_query (connection_name, sql)  执行查询（最多返回 100 行）
```

- 只查少量表：`dbx_get_schema_context` 一次拿全（max_tables 1~20），别再逐表 describe。
- 需要列级细节：`dbx_describe_table`。
- 存储过程：`dbx_list_routines` → 需要看源码用 `dbx_get_routine_source`。

## 查询规则

- SELECT / SHOW / 只读命令直接用 `dbx_execute_query`。
- 一脚本多语句（建临时表、USE/SET、跨语句依赖）：`dbx_execute_batch` 并传 `session_id`
  （先 `dbx_open_session`，用毕 `dbx_close_session`）。
- 多语句写操作要整体成功/回滚：`dbx_execute_batch` + `use_transaction: true`。
- 长字段值：`dbx_execute_query` 带 `cell_char_limit`/`cell_char_offset` 滑窗读取，别一次抓大字段。
- 查询结果先展示关键列与行数，量太大时聚合或加 LIMIT，等用户确认再扩。
- 结果给到用户用 Markdown 表格呈现，逐句核对口径（WHERE 条件、时间范围、空值），
  不与用户原始问题对齐就停下来确认。

## 写操作纪律（安全第一）

- 默认允许 `INSERT` / `UPDATE` / `DELETE`（普通写法），但每次写操作前必须：
  - 明确告知用户"将执行写操作 + 影响哪张表"，除非用户已显式要求执行写动作
  - 先 SELECT 预览将受影响的行（`WHERE` 对齐），再执行写
- 多语句写：`use_transaction: true`，出错过即回滚、不得半提交。
- `DROP` / `TRUNCATE` / `ALTER` / 无 WHERE 的 UPDATE/DELETE 属高危：
  - 默认被 DBX 策略拦截，若返回阻止，不得绕过（改 env、改策略都不行）
  - 用户要求删表/清表时，先要用户那只读/生产保护，明确危险后仅当 DBX 策略放行才执行
- 生产连接（DBX 里设了"生产保护"）一律严格只读；写操作被拒就如实报告，别想办法绕过。

## 消息队列 / Redis

- Redis：`dbx_execute_redis_command`，只读命令（GET/INFO/HLEN…）直接执行；
  写命令同"写操作纪律"。`FLUSH*`、`KEYS` 等危险命令被拦截时不要绕过。
- Kafka：`dbx_peek_messages`（默认最新 20 条，只读不提交 offset）；发送用
  `dbx_send_message`（需 base64 payload，属写操作，先向用户确认）。
- RabbitMQ/RocketMQ 发送同理走 `dbx_send_message`。

## UI 联动

- `dbx_open_table` / `dbx_execute_and_show`：需要 DBX 桌面端正在运行。
  用户想人眼确认数据或把结果留在 DBX 里再看时使用。

## 连接管理

- 新增/复制/删除连接：`dbx_add_connection` / `dbx_duplicate_connection` /
  `dbx_remove_connection`。删除连接属破坏性操作，仅当用户明确指定连接并要求删除时执行。

## 与 db-designer 联动

- 新表设计走 `db-designer` skill（产出 .erd.json / DDL）；完成后可用本 skill 在
  DBX 中对其实际连通的目标库执行 `dbx_get_schema_context` 核对列名/类型与字典一致。

## 产出约定

- 向用户汇报一律给出：连接名、库名、执行的 SQL 要点（非整段）、影响行数、来源表。
- 发现与用户描述不符的库/表/字段（命名、类型、缺失），停下并列出差异，不猜测拼写。