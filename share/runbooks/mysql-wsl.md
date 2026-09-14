# MySQL + Redis（圆头宝开发库，WSL2）

> 本机 WSL2 Ubuntu-22.04 上的 MySQL 8.0 与 Redis，为「圆头宝」项目（D:\dev\bbcare\yuantoubao）提供本地开发数据服务。

## 拓扑与版本

- 宿主：Windows 11（win32）；发行版：WSL2 `Ubuntu-22.04`
- MySQL：`mysql-server` 8.0.46（Ubuntu jammy-updates 源），端口 `3306`，`bind-address=0.0.0.0`（WSL 内）
- Redis：`redis-server` 6.0.16（Ubuntu jammy source），端口 `6379`，无密码（仅绑 `127.0.0.1`）
- 时区：MySQL 会话/服务器时区 `+08:00`；字符集：库表默认 `utf8mb4` / `utf8mb4_0900_ai_ci`
- 库：`yuantoubao`；应用账号：`ytb`

## 访问与账号策略

| 账号 | 用途 | 登录方式 |
|---|---|---|
| `root` | 管理 | `sudo mysql`（Ubuntu 默认 auth_socket，无密码） |
| `ytb` | 应用读写 `yuantoubao.*` | TCP `127.0.0.1:3306` + 密码（凭据见下，勿在此写值） |

- 应用连接串：`D:\dev\bbcare\secrets\yuantoubao.env`（`DATABASE_URL` / `REDIS_URL`，仓库外，不入库）。
- 测试库授权（2026-09-12）：`ytb`@`localhost` / `ytb`@`%` 另获 `GRANT ALL PRIVILEGES ON \`yuantoubao\_test%\`.*`，可自建/删除 `yuantoubao_test*`（pytest 测试库与并行任务隔离库）。
- DBX 客户端：连接名「yuantoubao (WSL2 MySQL)」，host `127.0.0.1`、端口 `3306`、库 `yuantoubao`、用户 `ytb`（密码存于 DBX 内部，来源为上述 env）。
- Windows→WSL 访问路径：
  1. `127.0.0.1:3306`（WSL localhost 转发，首选，DBX 用此路径）；
  2. WSL VM 的 IP（如 `172.22.x.x:3306`，直连备用；需 Hyper-V 防火墙放行规则「WSL-YTB-Inbound-TCP」，见部署记录）。

## 部署记录

- 安装：`sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server redis-server`（2026-09-11）
- 时区与绑定：新建 `/etc/mysql/mysql.conf.d/zz-ytb.cnf`，`[mysqld]` 段 `default-time-zone = +08:00`、`bind-address = 0.0.0.0`
- 建库建号：`CREATE DATABASE yuantoubao CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;`；创建 `ytb`@`localhost`/`ytb`@`%`，`GRANT ALL ON yuantoubao.*`；密码 `openssl rand -hex 16` 生成，写入凭据文件。
- 测试库授权（2026-09-12）：`GRANT ALL PRIVILEGES ON \`yuantoubao\_test%\`.*` 授 `ytb`@`localhost`/`%`；等价探针账号实测 CREATE/DROP 通过（探针已删）。
- 凭据文件：`D:\dev\bbcare\secrets\yuantoubao.env`（`umask 077` 落盘）。
- Windows 侧 Hyper-V 防火墙放行（2026-09-11，管理员执行）：
  `New-NetFirewallHyperVRule -Name "WSL-YTB-Inbound-TCP" -DisplayName "WSL yuantoubao inbound 3306/6379/80" -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -Protocol TCP -LocalPort 3306,6379,80 -Action Allow`
  （供 Windows 经 WSL IP 直连；撤销：`Remove-NetFirewallHyperVRule -Name "WSL-YTB-Inbound-TCP"`）
- **WSL VM 保活（关键组件）**：计划任务 `WSL-Ubuntu22.04-KeepAlive`（登录时启动、隐藏窗口），动作为常驻会话 `powershell -NoProfile -NonInteractive -WindowStyle Hidden -Command "wsl.exe -d Ubuntu-22.04 -e sleep infinity"`，用于阻止 WSL VM 空闲自动关机（见「已知限制」）。

## 运维手册

- 启动/停止/重启（WSL 内）：
  - MySQL：`sudo service mysql start|stop|restart`
  - Redis：`sudo service redis-server start|stop|restart`
- 日志：MySQL `/var/log/mysql/error.log`；Redis `/var/log/redis/redis-server.log`
- VM 与保活任务：
  - 查看 VM：`wsl -l -v`；启动 VM：任意 `wsl -d Ubuntu-22.04` 命令，或 `Start-ScheduledTask -TaskName "WSL-Ubuntu22.04-KeepAlive"`
  - 查看任务：`Get-ScheduledTask -TaskName "WSL-Ubuntu22.04-KeepAlive"`；临时停用：`Stop-ScheduledTask` / `Disable-ScheduledTask`（同名）
  - Windows 重启后：登录即触发保活任务自动拉起 VM，systemd 自启 mysql/redis；用 `systemctl is-active mysql redis-server` 确认。
- 排障（Windows 侧连不上 3306/6379/80 时，按序）：
  1. 查 VM 是否在运行：`wsl -l -v`（`Stopped` = 所有服务已停，启动 VM/保活任务即可）；
  2. 测真实握手（`Test-NetConnection` 会误报 True）：`python -c "import socket;s=socket.create_connection(('127.0.0.1',3306),timeout=5);print('OK')"`；
  3. 仍不通时 `wsl --shutdown` 后重启 VM 重建 localhost 转发；
  4. 检查保活任务与防火墙规则是否存在（见上）。
- 快捷连通检查（WSL 内）：`redis-cli ping` 应返回 `PONG`；`sudo mysql -e 'SELECT 1'`。

## 安全注意

- `zz-ytb.cnf`：本机开发配置（时区、bind-address），无敏感值。
- 凭据文件 `D:\dev\bbcare\secrets\yuantoubao.env` 含明文密码，勿提交/勿外发；撤销账号：`sudo mysql -e "DROP USER 'ytb'@'localhost'; DROP USER 'ytb'@'%';"`。
- `bind-address=0.0.0.0`：WSL 处于 NAT 之后、且 Hyper-V 防火墙默认拦截入站（另有显式放行规则），仅 Windows 宿主可达；Redis 仍仅绑 `127.0.0.1`。

## 已知限制

- **WSL VM 空闲自动关机（本 runbook 最大的坑）**：WSL 2.6.1.0 默认空闲约 60 秒即关闭整个 VM，MySQL/Redis/Kanboard 随之全部下线，Windows 侧连接被拒（`os error 10061`）。`C:\Users\qiu_k\.wslconfig` 中的 `[wsl2] vmIdleTimeout=2147483647` 实测**未能阻止**（值可能未被该版本接受）；实际由保活计划任务解决。**若保活任务被停用/删除，问题会复现。**
- Windows 重启后 VM 不会自行启动，需登录（触发保活任务）或手动执行任意 `wsl` 命令。
- systemd：`/etc/wsl.conf` 现为 `[boot] systemd=true`，`mysql` / `redis-server` 已 enable（VM 启动即自启）；若 systemd 不可用，退回手动 `sudo service mysql start` / `sudo service redis-server start`。

## 最近更新

- 2026-09-11 初装：MySQL 8.0.46 + Redis 6.0.16，建库建号，写凭据文件，登记本 runbook（对应任务书 P1-01）。
- 2026-09-11 排障与加固：定位「Windows→WSL 时通时断 / DBX 报 10061」根因为 **WSL VM 空闲自动关机**（非 relay、非防火墙、非 DBX 问题）；新增保活计划任务、Hyper-V 防火墙放行规则；DBX 接入（host `127.0.0.1`）；`bind-address` 定版 `0.0.0.0`。
- 2026-09-12：测试库授权落地（`ytb` 通配 `yuantoubao\_test%`，探针验证 CREATE/DROP 通过）；文档修正：systemd 已启用（mysql/redis 自启）、Hyper-V 防火墙规则 `WSL-YTB-Inbound-TCP` 已启用（复核存在）。
