---
name: mockoon-env
description: >
  Mockoon 环境文件（mock 服务配置）生成与维护。Use when generating or editing
  Mockoon environment JSON, running mock servers with mockoon-cli, or mocking
  APIs for frontend/integration development. Triggers: mock, mockoon, 模拟服务,
  mock server, mockserver, 生成mock配置, mock接口.
---

# Mockoon 环境生成（mockoon-env）

## 适用

- 为前后端联调/集成测试生成或修改 Mockoon 环境 JSON（v9 格式）
- 用 mockoon-cli 校验、启动、冒烟 mock 服务
- 不适用：桌面版 GUI 操作（本项目不装桌面版）

## 事实源

| 内容 | 来源 |
|---|---|
| 接口语义/路径/状态码/权限 | 项目 `design/api/*.md`（公共约定 + 分端清单） |
| 字段级 schema | 项目 `design/db/*`（ERD/数据字典）参考；最终以 backend OpenAPI（P1 落地后）为准 |
| 环境文件结构 | `reference/environment-schema.md`（官方 v9 schema 提炼） |
| 存放与端口 | 项目 `mock/README.md`（圆头宝：`mock/environments/`，h5=4010 / admin=4011） |

## 工作流

1. 读契约：从 design/api 提取方法、路径、入参、响应语义、错误码
2. 定环境：确认目标文件（h5.json / admin.json）与端口，不新建重复环境
3. 写路由：一个接口一个 route；响应体按契约 snake_case、金额分、时间 +08:00
4. 同步 rootChildren：每条 route 在 `rootChildren` 加 `{type:"route", uuid}`（漏了不显示/不生效）
5. 校验：`mockoon-cli validate --data <文件>`，必须全过
6. 起服冒烟：start（或 MCP `start_mock`）→ curl 断言 → stop
7. 登记：新增环境文件/端口时更新项目 `mock/README.md`

## 硬规则

- `endpoint` 不带前导 `/`（如 `api/v1/me`）
- 响应 `body` 是**字符串**（内嵌 JSON 需转义）；`bodyType: "INLINE"`
- uuid 全文件唯一；修改时保持既有 uuid 稳定（避免 diff 噪音）
- `lastMigration` 用当前 CLI 支持值（9.8.0 为 33）；不确定时以 validate 为准
- 多响应切换用 `label` + `rules` + `rulesOperator`；兜底响应 `default: true`
- 回调是**两层结构**：环境级 `callbacks[]`（定义，字段 `uri`）+ 响应内 `callbacks: [{uuid, latency}]`（引用）；不存在 `url/delay` 字段（旧格式写法会被静默丢弃）
- 默认 `cors: true`（跨端口联调需要）
- 不加 schema 之外的自定义字段（会被 stripUnknown 丢弃）

## 常用模式

- 成功/付费墙切换：多响应 + query/header 规则 → `templates/multi-response-rules.json`
- 异步回调/状态翻转：环境级 callbacks + 响应引用 → `templates/callback.json`；复杂状态用 Data Bucket
- 动态数据：`{{faker 'person.fullName'}}`、`{{body 'field'}}`、`{{queryParam 'x'}}`、`{{header 'x'}}`

## 集成测试衔接（编码期）

- 被测方（h5/admin dev）将 API BaseUrl 指向 mock（如 `http://localhost:4010`）
- 核对序列化方向（契约 snake_case）与字段名
- 成功/失败/边界用多响应可切换；第三方回调（微信/支付）用 callbacks 模拟
- 核对"收到的入参"：响应体回显 `{{body 'field'}}` 或查 `--log-transaction` 日志

## 自检清单

- [ ] validate 全过
- [ ] 每条 route 都在 rootChildren 有引用
- [ ] 起服后 curl 新路由，状态码/结构与契约一致
- [ ] 响应字段命名 snake_case、金额分、时间 +08:00
- [ ] 端口无冲突；MCP `list_mocks` 可见（MCP 注册后）

## 参考

- `reference/environment-schema.md` — v9 字段全表、规则枚举、回调结构、坑
- `reference/cli-cheatsheet.md` — validate/start/import/export/MCP/排障
- `templates/` — minimal / multi-response-rules / callback
