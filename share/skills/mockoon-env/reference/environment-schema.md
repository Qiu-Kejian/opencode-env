# Mockoon v9 环境文件字段参考

> 来源：官方 schema 源码 `packages/commons/src/constants/environment-schema.constants.ts`（main，9.8.0 时代）+ `mockoon-cli validate` 实测。字段名/枚举以此为准；写完后必须 validate。

## 顶层（全部必填）

| 字段 | 类型/取值 | 说明 |
|---|---|---|
| `uuid` | UUID | 环境唯一 ID |
| `lastMigration` | number | 格式版本；9.8.0 为 `33` |
| `name` | string | 环境名（日志文件名用） |
| `endpointPrefix` | string | 全局路径前缀，默认 `""` |
| `latency` | number ≥0 | 全局延迟 ms |
| `port` | number 0-65535 | 默认 3000；本项目 h5=4010 / admin=4011 |
| `hostname` | string | `""`=默认（localhost 可访问） |
| `rootChildren` | `{uuid,type:route\|folder}[]` | 树顺序引用；**每条 route/folder 都要在此出现** |
| `folders` | Folder[] | 见下 |
| `routes` | Route[] | 见下 |
| `proxyMode` / `proxyHost` / `proxyRemovePrefix` | bool / string / bool | 代理模式（默认 false） |
| `tlsOptions` | object | `{enabled:false, type:"CERT", pfxPath:"", certPath:"", keyPath:"", caPath:"", passphrase:""}` |
| `cors` | bool | `true` 时自动加 CORS 头 |
| `headers` / `proxyReqHeaders` / `proxyResHeaders` | Header[] | `{key,value}`，均可空串 |
| `data` | DataBucket[] | 数据桶（有状态 mock） |
| `callbacks` | Callback[] | 环境级回调定义 |

## Route

| 字段 | 类型/取值 |
|---|---|
| `uuid` | UUID |
| `type` | `http` \| `crud` \| `ws` |
| `documentation` | string |
| `method` | `all` \| `get` \| `post` \| `put` \| `patch` \| `delete` \| `head` \| `options` \| `propfind` \| `proppatch` \| `move` \| `copy` \| `mkcol` \| `lock` \| `unlock` |
| `endpoint` | string，**无前导 `/`**，支持 `:param` 路径参数 |
| `responses` | RouteResponse[] |
| `responseMode` | `null` \| `RANDOM` \| `SEQUENTIAL` \| `DISABLE_RULES` \| `FALLBACK` |
| `streamingMode` | `null` \| `UNICAST` \| `BROADCAST` |
| `streamingInterval` | number ≥0 |

## RouteResponse

| 字段 | 类型/取值 |
|---|---|
| `uuid` | UUID |
| `body` | **string**（内嵌 JSON 需转义；模板变量在字符串内生效） |
| `latency` | number ≥0（ms） |
| `statusCode` | 100-999 |
| `label` | string（多响应切换时人读标签） |
| `headers` | Header[] |
| `bodyType` | `INLINE` \| `DATABUCKET` \| `FILE` |
| `filePath` / `databucketID` | string（按 bodyType 使用） |
| `sendFileAsBody` | bool |
| `rules` | ResponseRule[]（见下） |
| `rulesOperator` | `OR` \| `AND` |
| `disableTemplating` | bool |
| `fallbackTo404` | bool |
| `default` | bool（无规则命中时的兜底响应，仅一个） |
| `crudKey` | string（默认 `id`） |
| `callbacks` | `{uuid, latency}[]` — **仅引用**环境级 callbacks |

### ResponseRule

| 字段 | 取值 |
|---|---|
| `target` | `body` \| `query` \| `header` \| `cookie` \| `params` \| `path` \| `method` \| `request_number` \| `global_var` \| `data_bucket` \| `templating` |
| `modifier` | string（如 query 的参数名、body 的 JSONPath） |
| `value` | string（比较值） |
| `operator` | `equals` \| `regex` \| `regex_i` \| `null` \| `empty_array` \| `array_includes` \| `valid_json_schema` |
| `invert` | bool |

例：query 参数 `entitled=1` 命中 → `{target:"query", modifier:"entitled", value:"1", operator:"equals", invert:false}`。

## Folder / rootChildren 条目

`{uuid, name, children:[{uuid, type:"route"|"folder"}]}`；`rootChildren` 条目为 `{uuid, type}`。

## Callback（环境级定义）

| 字段 | 类型/取值 |
|---|---|
| `uuid` / `id` | UUID / string |
| `name` / `documentation` | string |
| `method` | 同 Route.method（常用 `post`） |
| `uri` | string，目标 URL；可用相对路径（按 mock 自身地址解析）或 `{{baseUrl}}/...` |
| `headers` | Header[] |
| `bodyType` | `INLINE` \| `DATABUCKET` \| `FILE` |
| `body` / `filePath` / `databucketID` | string |
| `sendFileAsBody` | bool |

响应内引用：`"callbacks": [{"uuid": "<环境级回调uuid>", "latency": 3000}]`。

> 注意：旧版/网络示例里的 `{url, delay}` 直挂响应写法在 v9 无效，会被 schema 静默丢弃。

## DataBucket

`{uuid, id, name, documentation, value}`，`value` 为 JSON 字符串（默认 `"[\n]"`）。响应 `bodyType:"DATABUCKET"` + `databucketID` 读取；可配 CRUD 路由做有状态 mock。

## 模板速查（响应 body 内）

| 语法 | 用途 |
|---|---|
| `{{body 'a.b'}}` / `{{bodyRaw 'a.b'}}` | 请求体字段（转义/不转义） |
| `{{queryParam 'x'}}` / `{{urlParam 'id'}}` / `{{header 'name'}}` / `{{cookie 'name'}}` | 请求参数 |
| `{{faker 'person.fullName'}}` | 随机数据（`--faker-locale`/`--faker-seed` 可固定） |
| `{{date 'YYYY-MM-DD'}}` | 日期格式化 |
| `{{baseUrl}}` | 本 mock 服务地址 |
| `{{getEnvVar 'MOCKOON_X'}}` | 环境变量（前缀可配） |
| `{{setVar 'x' 'v'}}` / `{{getVar 'x'}}` | 请求内局部变量 |

完整清单见官方 templating 文档（mockoon.com/docs/latest/templating/overview/）。

## 常见坑

1. **rootChildren 漏同步**：route 存在于 `routes` 但不在 `rootChildren` → 树中不可见/不生效。
2. **endpoint 带前导 `/`**：路由匹配异常。
3. **body 直接写 JSON 对象**：schema 要求 string；对象会被修复为默认值，响应变 `{}`。
4. **回调写成单层 `{url,delay}`**：静默丢失，回调不触发。
5. **lastMigration 落后**：CLI 启动会自动迁移副本（不改原文件）；桌面版新版保存的文件需升级 CLI。
6. **未知字段**：schema `stripUnknown` 直接丢弃，不会报错——validate 通过≠字段生效。
7. **端口冲突**：`--port` 覆盖或改文件；起服失败先查占用。
