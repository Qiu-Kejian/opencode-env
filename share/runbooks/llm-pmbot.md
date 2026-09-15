# pm-bot（Kanboard 看板 PM agent）+ 模型驱动运维手册

> 状态：运行中 · 最近更新：2026-09-15（pm-bot 改用 opencode 免费模型 `opencode/big-pickle` 驱动；公共层移除 `provider.ollama`）

## 1. 拓扑与版本

| 项 | 值 |
|----|----|
| PM agent | `.opencode/agent/pm-bot.md`（工作区公共层，mode=**subagent**） |
| 驱动模型 | `opencode/big-pickle`（opencode 免费模型；替代此前的 `deepseek/deepseek-v4-flash`） |
| Kanboard | WSL2 原生 v1.2.54，`http://localhost`（部署/运维见 `kanboard-wsl.md`） |
| Kanboard 工具 | `tools/kb.py`（JSON-RPC CLI，零第三方依赖） |
| 凭据 | `C:\Users\qiu_k\.config\opencode\kanboard.env`（KB_USER=pm-bot / KB_TOKEN / KB_PROJECT=圆头宝 / KB_OPS_LOG），**勿提交 git** |
| 审计日志 | `logs/kb-ops.log`（create/move/comment 全量追加） |

## 2. 关键文件

- pm-bot agent 定义：`.opencode/agent/pm-bot.md`（model=`opencode/big-pickle`，temperature 0.1，写权限仅限 `kb.py`）
- Kanboard API 授权：WSL `/var/www/kanboard/data/db.sqlite` 中用户 `pm-bot`(id=3, role app-admin, `api_access_token` 明文列) + 项目 1「圆头宝」project-manager 成员行（`project_has_users`）
- 说明：工作区公共层 `opencode.json` **已移除 `provider.ollama`**（原本地 Ollama 供应商）；pm-bot 不再依赖本机 GPU / 本地模型，纯走 opencode 托管模型。

## 3. 日常用法（供主 agent 委托 pm-bot）

在任意 opencode 项目会话，可直接唤起子 agent `pm-bot`，或本机直接跑：
```bash
python .opencode/tools/kb.py open                  # 未完成卡
python .opencode/tools/kb.py by-fr FR-ACC-01       # 按 FR 查
python .opencode/tools/kb.py create -t "..." --fr FR-XX-01 --col 待办
python .opencode/tools/kb.py move 5 -c 进行中 --comment "commit abc"
python .opencode/tools/kb.py log                   # 审计
```
看板列（圆头宝项目）：`待办 / 预备 / 进行中 / 待验收 / 完成`。
卡 reference 约定：FR 卡 = `FR-xx-nn`；P1 施工单卡 = `P1-xx`。状态同步协议见 bbcare `taskbooks/README.md`（执行侧直写开工/收尾，完成/返工人工终审）。

## 4. 排障速查

- **opencode 里看不到 pm-bot / big-pickle**：改过 `opencode.json`/agent 需重启 opencode；模型列表应见 `opencode/big-pickle`（可 `/models` 确认）。
- **big-pickle 报错 / 限流 / 不可用**：opencode 免费模型有额度与并发限制；在 `.opencode/agent/pm-bot.md` 用 `model:` 临时覆盖回 `deepseek/deepseek-v4-flash` 应急。
- **kb.py 报 403**：确认用户 `pm-bot` 是该项目的 project-manager（DB `project_has_users`）。
- **Kanboard 不可达**：见 `kanboard-wsl.md`（WSL 里 `sudo systemctl status apache2`）。
- **凭据轮换**：生成新 token 写回 DB（`UPDATE users SET api_access_token='...' WHERE username='pm-bot'`）并同步 `kanboard.env`。

## 5. 已知限制与注意

- **pm-bot 模型决策**：曾绑本地 `qwen3-pm:8b`（num_ctx 8192，8GB 显存全 GPU / 33 tok/s），因上下文短、会话反复压缩、能力不足，改与主 agent 同模型 `deepseek/deepseek-v4-flash`；现为省额度改用 opencode 免费模型 `opencode/big-pickle`。本地 Ollama 供应商配置已从公共层移除，端点仅余手动实验用途。
- `kb.py` 仅模板化读写；删除/改权限等需人工在 UI 做。列配置（增列 / 调序）不在 kb.py 内：经 JSON-RPC `addColumn` / `changeColumnPosition` / `updateColumn` / `removeColumn`（2026-09-12 新增「待验收」列时使用；列内有卡不可删）。
- 项目名「圆头宝」与仓库文档常用「园头宝」字形不同，以 Kanboard 实际为准。
