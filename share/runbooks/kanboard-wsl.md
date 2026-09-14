# Kanboard 部署与运维手册（WSL2 / Ubuntu）

> 状态：运行中 · 最近更新：2026-09-08（初始部署）

## 1. 拓扑与版本

| 项 | 值 |
|----|----|
| 运行环境 | Windows 主机 + WSL2，发行版 `Ubuntu-22.04`（用户 `qiu`，NOPASSWD sudo） |
| 安装方式 | WSL 内原生安装（**非 Docker**，SQLite 方案官方禁止跑 Docker） |
| Web 服务 | Apache 2.4.52（Ubuntu），默认端口 80 |
| PHP | 8.1.2（Ubuntu 自带，满足 Kanboard ≥ 8.1） |
| Kanboard | **v1.2.54**（最新稳定版，来自 GitHub release 源码包） |
| 数据库 | SQLite（单用户/个人用），首启自动生成 |
| 安装路径 | `/var/www/kanboard`（WSL 原生 ext4） |
| 属主 | `www-data:www-data` |
| 访问 URL | `http://localhost`（Windows 浏览器直通 WSL2），登录页 `/login` |
| 自启动 | systemd（`/etc/wsl.conf` 已 `systemd=true`），apache2 服务 `enabled` |

## 2. 访问与账号策略

- 首次登录默认账号 `admin` / `admin`。
- **首登后务必在个人资料中修改密码**（Kanboard 无强制改密，需手动）。
- 单用户 SQLite 无需额外 cron 后台任务；若日后多人并发，应迁移 MariaDB/Postgres 并补 cron。

## 3. 部署记录

依赖安装：
```bash
sudo apt-get install -y apache2 php php-sqlite3 php-gd php-mbstring php-xml php-curl php-zip unzip wget
# 校验扩展：pdo_sqlite gd mbstring curl zip xml SimpleXML dom session openssl 均已装
```

部署 Kanboard（升级可复用同一套命令，见 §4）：
```bash
cd /tmp && wget https://github.com/kanboard/kanboard/archive/refs/tags/v1.2.54.tar.gz
sudo tar xzf v1.2.54.tar.gz -C /var/www
sudo mv /var/www/kanboard-1.2.54 /var/www/kanboard
sudo chown -R www-data:www-data /var/www/kanboard
```

Apache 关键配置（`/etc/apache2/sites-available/000-default.conf`，默认 vhost 已改）：
- `DocumentRoot /var/www/kanboard`
- 目录节：`Options -Indexes +FollowSymLinks`、`AllowOverride All`（启用 Kanboard 自带 `.htaccess` 美化 URL）、`Require all granted`
- `a2enmod rewrite` 已启用

## 4. 运维手册

日常命令（在 Windows 终端经 `wsl -d Ubuntu-22.04 --` 执行，或 WSL 内直接执行）：
```bash
sudo systemctl restart apache2   # 改配置/排障后重启
sudo systemctl status apache2    # 查看状态
sudo service apache2 start       # 手动启动
```

**备份**（核心，整包复制 `data/` 即含数据库+附件）：
```bash
sudo cp -a /var/www/kanboard/data /backup/kanboard-data-$(date +%F)
```

**升级 Kanboard**（如 v1.2.54 → v1.2.55）：
```bash
cd /tmp && wget https://github.com/kanboard/kanboard/archive/refs/tags/v1.2.55.tar.gz
# 1) 先备份 data
sudo cp -a /var/www/kanboard/data /backup/kanboard-data-before-upgrade
# 2) 新包解压到 /var/www，覆盖安装目录，保留原 data
sudo tar xzf v1.2.55.tar.gz -C /var/www
sudo cp -a /var/www/kanboard/data/. /var/www/kanboard-1.2.55/data/
sudo rm -rf /var/www/kanboard && sudo mv /var/www/kanboard-1.2.55 /var/www/kanboard
sudo chown -R www-data:www-data /var/www/kanboard
# 3) 浏览器刷新首页触发数据库迁移
```

**故障排查**：
- 页面打不开：先看日志 `sudo tail -f /var/log/apache2/error.log`
- 权限报错：确认属主 `sudo chown -R www-data:www-data /var/www/kanboard`
- 端口占用（80 被占）：改 vhost `Listen`/`<VirtualHost *:8080>` 后重启并同步防火墙
- 服务未随 WSL 启动：`sudo systemctl enable apache2`；检查 `/etc/wsl.conf` 是否含 `systemd=true`

**回滚**：
```bash
sudo systemctl stop apache2 && sudo rm -rf /var/www/kanboard   # 停止并删除
sudo apt-get purge -y apache2 php*                              # 如彻底移除
```

## 5. 安全注意

- 安装期曾为 WSL 用户 `qiu` 加 NOPASSWD sudoers：`/etc/sudoers.d/qiu-nopasswd`（内容 `qiu ALL=(ALL) NOPASSWD: ALL`）。如需撤销：`sudo rm /etc/sudoers.d/qiu-nopasswd`。
- 默认服务仅监听 localhost，未对外开放；如长期使用建议规划备份策略与更新提醒。

## 6. 已知限制

- **SQLite 不得跑在 Docker/NFS 上**（官方明确警告），本方案即因此选择 WSL 原生安装。
- 代码/数据必须留在 WSL 原生 ext4（`/var/www/...`）；**勿放 `/mnt/c`**（Windows 盘经 9P 协议 IO 慢、文件锁有风险）。
- 单用户 SQLite 并发弱，多人团队需换 MariaDB/Postgres。
- 默认无 HTTPS、未接入邮件/到期提醒等后台任务。
