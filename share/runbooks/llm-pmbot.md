# 本地 Ollama 模型 + pm-bot agent 运维手册

> 状态：运行中 · 最近更新：2026-09-12（看板加「待验收」列 + 三层同步协议）

## 1. 拓扑与版本

| 项 | 值 |
|----|----|
| 推理引擎 | Ollama 0.33.3（Windows 原生，OpenAI 兼容端点 `http://localhost:11434/v1`） |
| GPU | RTX 5060 Laptop **8GB**（8151MiB，驱动 582.05，CUDA 13） |
| 本地模型 | `qwen3:8b`（底座 Q4 5.2GB）+ 别名 `qwen3-pm:8b`（num_ctx=8192, temp=0.2）。**备用**：本地模型上下文受限致压缩，pm-bot 现不用本地模型 |
| pm-bot agent | `.opencode/agent/pm-bot.md`（工作区公共层，mode=**subagent**，model=**deepseek/deepseek-v4-flash** 与主 agent 一致） |
| Kanboard 工具 | `tools/kb.py`（JSON-RPC CLI，零第三方依赖） |
| 凭据 | `C:\Users\qiu_k\.config\opencode\kanboard.env`（KB_USER=pm-bot / KB_TOKEN / KB_PROJECT=圆头宝 / KB_OPS_LOG），**勿提交 git** |
| 审计日志 | `logs/kb-ops.log`（create/move/comment 全量追加） |

## 2. 关键文件

- opencode provider 配置：`.opencode/opencode.json` → `provider.ollama`（npm `@ai-sdk/openai-compatible`，baseURL 11434/v1）
- Kanboard API 授权：WSL `/var/www/kanboard/data/db.sqlite` 中用户 `pm-bot`(id=3, role app-admin, `api_access_token` 明文列) + 项目 1「圆头宝」project-manager 成员行（`project_has_users`）
- 调优模型 Modelfile：`FROM qwen3:8b` + `PARAMETER num_ctx 8192` + `temperature 0.2`（已生成为 qwen3-pm:8b）

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

- **模型变慢**：`ollama ps` 看 PROCESSOR —— 非 100% GPU 则 num_ctx 过大或换模型被加载；等待或 `ollama stop` 清场。
- **opencode 里看不到 pm-bot / ollama 模型**：改过 `opencode.json`/agent 需重启 opencode；`/models` 应见 `Ollama (local)`。
- **kb.py 报 403**：确认用户 `pm-bot` 是该项目的 project-manager（DB `project_has_users`）。
- **Kanboard 不可达**：见 `kanboard-wsl.md`（WSL 里 `sudo systemctl status apache2`）。
- **凭据轮换**：生成新 token 写回 DB（`UPDATE users SET api_access_token='...' WHERE username='pm-bot'`）并同步 `kanboard.env`。

## 5. 已知限制与注意

- **pm-bot 模型决策**：曾绑本地 qwen3-pm:8b（num_ctx 8192 → 100% GPU / 33 tok/s），但上下文短、会话反复压缩、能力不足，已改与主 agent 同模型 `deepseek/deepseek-v4-flash`。本地模型保留备用，仅 Ollama 端点仍可用于实验。
- 本地 8GB 显存只能全 GPU 跑 ~8B 且需压上下文；Ollama 默认 40K ctx 会爆 8GB（半卸 CPU 跌到 ~9 tok/s）。
- `kb.py` 仅模板化读写；删除/改权限等需人工在 UI 做。列配置（增列 / 调序）不在 kb.py 内：经 JSON-RPC `addColumn` / `changeColumnPosition` / `updateColumn` / `removeColumn`（2026-09-12 新增「待验收」列时使用；列内有卡不可删）。
- 项目名「圆头宝」与仓库文档常用「园头宝」字形不同，以 Kanboard 实际为准。
