# mockoon-cli 速查（9.8.0）

## 安装与版本

```powershell
npm install -g @mockoon/cli@9.8.0   # MCP 需 ≥9.8.0；Node ≥18
mockoon-cli --version
```

## validate（改完环境文件必跑）

```powershell
mockoon-cli validate --data .\environments\h5.json .\environments\admin.json
```

## start

```powershell
# 多环境一起起（端口取各自文件 port）
mockoon-cli start --data .\environments\h5.json .\environments\admin.json

# 常用：监听文件变更（轮询 2s）+ 覆盖端口 + 固定 faker
mockoon-cli start --data .\environments\h5.json --watch --port 4010 --faker-locale zh_CN --faker-seed 42

# 排查：打印完整请求/响应事务
mockoon-cli start --data .\environments\h5.json --log-transaction
```

| Flag | 用途 |
|---|---|
| `-d, --data` | 环境文件（可多个；支持 URL / `cloud://`） |
| `-p, --port` | 覆盖端口（与 data 顺序对应） |
| `-l, --hostname` | 覆盖监听地址（默认 `0.0.0.0`） |
| `-w, --watch` / `--polling-interval` | 文件变更自动重启 |
| `-c, --faker-locale` / `-s, --faker-seed` | faker 语言/种子（可复现） |
| `-t, --log-transaction` | 事务日志 |
| `-e, --disable-routes` | 按 UUID/路径关键字禁用路由（调试） |
| `--proxy` | 覆盖代理开关（enabled/disabled） |
| `-r, --repair` | 迁移/修复过旧数据文件 |
| `--disable-admin-api` / `--admin-api-token` | 管理 API 开关/令牌（默认开启，自动生成令牌） |
| `--max-request-body-size` | 请求体上限（默认 100MB） |

## import / export

```powershell
mockoon-cli import --input .\openapi.yaml --output .\environments\h5.json --prettify
mockoon-cli export --input .\environments\h5.json --output .\openapi.json --prettify
```

- `import` 支持 Swagger v2 / OpenAPI v3（JSON/YAML）；导入的字段映射不完整，复杂行为（templating/rules）会丢失，适合起骨架。
- `export` 输出 OpenAPI v3；可作为与 backend OpenAPI 对账的手段。

## MCP（全局 opencode.json 注册；机器路径留在全局层）

```jsonc
// ~/.config/opencode/opencode.json
"mockoon": {
  "command": ["C:\\Users\\qiu_k\\AppData\\Roaming\\npm\\mockoon-cli.cmd", "mcp"],
  "enabled": true,
  "type": "local",
  "env": { "MOCKOON_DATA_DIRS": "D:\\dev\\bbcare\\yuantoubao\\mock\\environments" }
}
```

工具：`list_mocks`（列目录内环境）、`start_mock`、`stop_mock`、`list_running_mocks`。`MOCKOON_DATA_DIRS` 分号分隔多目录；改配置后需重启 opencode。

## 日志与排障

- 日志：`~/.mockoon-cli/logs/{环境名}.log`；stdout 同时输出。
- 端口占用：`Get-NetTCPConnection -LocalPort 4010 -State Listen`；换 `--port` 或改文件。
- 停服：前台 Ctrl+C；后台 `Stop-Process -Id <pid>`（`Start-Process -PassThru` 拿 pid）。

## Windows 后台启动

```powershell
$p = Start-Process mockoon-cli -ArgumentList 'start','--data','.\environments\h5.json' -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2
curl.exe -s http://localhost:4010/health
Stop-Process -Id $p.Id
```

## 冒烟断言

```powershell
curl.exe -s http://localhost:4010/health
curl.exe -s -X POST http://localhost:4010/api/v1/auth/wx-login -H "Content-Type: application/json" -d "{\"code\":\"test\"}"
```

核对"收到的入参"：响应体里回显 `{{body 'field'}}`，或用 `--log-transaction` 查日志。
