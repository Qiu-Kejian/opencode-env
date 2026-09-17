#!/usr/bin/env python3
"""批次门机器验收器（骨架 · 通用版）。

用法（任意目录）：
    python <ORCH>/tools/acceptance.py --sprint <S> [--tasks T-...] [--repo <REPO>] [--report <path>]
    python <ORCH>/tools/acceptance.py --milestone <M> [--repo <REPO>] [--report <path>]

双根：ORCH = 编排实例目录（默认 = 本脚本父目录的上一级）；REPO = 产品仓库根
（--repo / 环境变量 ORCH_REPO / 默认=<ORCH> 的父目录）。
契约：退出码 = 判定（0 = 全 PASS；1 = 有 FAIL）；报告写 `<ORCH>/runs/<label>-acceptance.md`，
结论行含 `**PASS**` / `**FAIL**`（供 milestone 机读块聚合）。
本项目专属检查（静态 / 分层测试 / 迁移 / 前端 / 端到端）留 TODO，用 `record(...)` 注册。
纪律：退出码驱动；不打印任何 DSN；命令清单事实源为项目命令区，改门禁须同步本脚本。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ORCH = Path(__file__).resolve().parents[1]
Results = list[tuple[str, bool, str, str]]


def sh(cmd: list[str], cwd: Path) -> tuple[int, str]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [str(part) for part in cmd],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()


def last_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return ""


def record(results: Results, name: str, ok: bool, summary: str, output: str = "") -> None:
    results.append((name, ok, summary, output))


# --- 通用检查 -------------------------------------------------------------

def check_git_clean(results: Results, repo: Path, exempt: list[str]) -> None:
    if not (repo / ".git").exists():
        record(results, "仓库·git 干净", False, f"{repo} 不是 git 仓库")
        return
    code, out = sh(["git", "status", "--short"], repo)
    kept = [
        line
        for line in out.splitlines()
        if line.strip() and not any(pat and pat in line for pat in exempt)
    ]
    record(results, "仓库·git 干净", code == 0 and not kept, f"exit={code}; 未提交={len(kept)}", "\n".join(kept))


def check_evidence(results: Results, orch: Path, tasks: list[str]) -> None:
    missing = []
    for task_id in tasks:
        path = orch / "runs" / f"{task_id}.md"
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(task_id)
    record(results, "证据·runs 完整性", not missing, f"缺失={missing or '无'}", "\n".join(missing))


def check_project_static(results: Results, repo: Path) -> None:
    # TODO(项目): 静态检查（如 ruff / mypy / eslint / tsc）。示例：
    # run_exit0(results, "静态·ruff", ["python", "-m", "ruff", "check", "."], repo)
    record(results, "静态·项目门", True, "[TODO] 未配置项目静态检查")


def check_project_tests(results: Results, repo: Path) -> None:
    # TODO(项目): 分层测试 / 迁移升降 / 前端门 / 端到端。示例：
    # run_exit0(results, "测试·全量", ["python", "-m", "pytest", "-q"], repo)
    record(results, "测试·项目门", True, "[TODO] 未配置项目测试门")


def check_sensitive(results: Results, orch: Path, repo: Path) -> None:
    # TODO(项目): 敏感文件扫描（.env / 密钥关键词）。示例：
    # code, out = sh(["git", "ls-files"], repo)
    # hit = [f for f in out.splitlines() if f.endswith((".env", ".env.local"))]
    # record(results, "安全·敏感文件", not hit, f"命中={hit or '无'}", "\n".join(hit))
    record(results, "安全·敏感文件", True, "[TODO] 未配置敏感扫描")


# --- 报告 -----------------------------------------------------------------

def write_report(report: Path, label: str, results: Results, repo: Path) -> None:
    branch = head = "n/a"
    if (repo / ".git").exists():
        _, branch = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
        _, head = sh(["git", "log", "-1", "--format=%h %s"], repo)
    passed = all(ok for _, ok, _, _ in results)
    lines = [
        f"# 批次门验收报告 · {label}",
        "",
        f"- 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ｜ 编排目录：`{ORCH}` ｜ 产品仓库：`{repo}`",
        f"- 分支：`{branch}` ｜ HEAD：`{head}`",
        f"- 结论：**{'PASS' if passed else 'FAIL'}**",
        "",
        "| 检查 | 结论 | 摘要 |",
        "|---|---|---|",
    ]
    for name, ok, summary, _ in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {summary} |")
    lines.append("")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="批次门机器验收器（骨架）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sprint")
    group.add_argument("--milestone")
    parser.add_argument("--tasks", default="", help="逗号分隔的任务号（证据完整性用）")
    parser.add_argument("--repo", default="", help="产品仓库根（默认 ORCH_REPO 或 ORCH 的父目录）")
    parser.add_argument("--report", default="", help="报告路径（默认 <ORCH>/runs/<label>-acceptance.md）")
    args = parser.parse_args(argv)

    repo = Path(args.repo) if args.repo else Path(os.environ.get("ORCH_REPO", ORCH.parent))
    label = args.sprint or f"{args.milestone}-milestone"
    report = Path(args.report) if args.report else ORCH / "runs" / f"{label}-acceptance.md"
    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]

    results: Results = []
    check_git_clean(results, repo, exempt=[])
    check_evidence(results, ORCH, tasks)
    check_project_static(results, repo)
    check_project_tests(results, repo)
    check_sensitive(results, ORCH, repo)
    write_report(report, label, results, repo)

    passed = all(ok for _, ok, _, _ in results)
    for name, ok, summary, _ in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {summary}")
    print(f"\n报告：{report}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
