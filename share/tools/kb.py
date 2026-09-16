#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kb.py - Kanboard JSON-RPC 客户端 CLI（pm-bot 专用工具）。

只读:  ls / open / get / by-fr / log
写操作: create / move / comment   （模板化，全部写审计日志；支持 --dry-run）

用法示例:
  py kb.py ls -p 园头宝
  py kb.py open
  py kb.py get 12
  py kb.py by-fr FR-ACC-01
  py kb.py create -t "标题" --fr FR-ACC-01 --desc "..." --col 待办
  py kb.py move 12 -c 进行中 --comment "commit abc"
  py kb.py comment 12 -m "备注"
  py kb.py log
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ENV_FILE = Path.home() / ".config" / "opencode" / "kanboard.env"


def load_conf():
    conf = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            conf[k.strip()] = v.strip()
    return {
        "base_url": os.environ.get("KB_BASE_URL", conf.get("KB_BASE_URL", "http://localhost/jsonrpc.php")),
        "user": os.environ.get("KB_USER", conf.get("KB_USER", "pm-bot")),
        "token": os.environ.get("KB_TOKEN", conf.get("KB_TOKEN", "")),
        "project": os.environ.get("KB_PROJECT", conf.get("KB_PROJECT", "园头宝")),
        "ops_log": os.environ.get("KB_OPS_LOG", conf.get("KB_OPS_LOG", str(Path.home() / ".config" / "opencode" / "logs" / "kb-ops.log"))),
    }


CONF = load_conf()


def out(text=""):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def rpc(method, params=None, conf=None):
    conf = conf or CONF
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "id": 1, "params": params or {}}).encode("utf-8")
    token = (conf["user"] + ":" + conf["token"]).encode("utf-8")
    req = urllib.request.Request(
        conf["base_url"],
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Basic " + base64.b64encode(token).decode("ascii"),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            detail = ""
        raise RuntimeError("HTTP %d %s %s".strip() % (e.code, detail, ""))
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    return data.get("result")


def project_id(conf, name=None):
    name = name or conf["project"]
    for p in rpc("getAllProjects", {}, conf) or []:
        if p["name"] == name or p.get("identifier", "").upper() == name.upper():
            return p["id"]
    raise RuntimeError("项目不存在: %s" % name)


def columns(pid, conf):
    return rpc("getColumns", {"project_id": pid}, conf) or []


def resolve_column(pid, title, conf):
    cols = columns(pid, conf)
    if not title:
        cols = [c for c in cols if c["title"] != "完成"]
        return cols[0]["id"]
    for c in cols:
        if c["title"] == title:
            return c["id"]
    for c in cols:
        if c["title"].startswith(title):
            return c["id"]
    raise RuntimeError("列不存在: %s（现有: %s）" % (title, " / ".join(c["title"] for c in cols)))


def col_title_map(pid, conf):
    return {c["id"]: c["title"] for c in columns(pid, conf)}


def all_tasks(pid, conf):
    return rpc("getAllTasks", {"project_id": pid}, conf) or []


def find_task(tid, pid, conf, colmap):
    tasks = all_tasks(pid, conf)
    needle = str(tid).strip()
    for t in tasks:
        if str(t["id"]) == needle:
            return t
    for t in tasks:
        ref = str(t.get("reference") or "")
        if ref and ref.upper() == needle.upper():
            return t
    raise RuntimeError("任务不存在: %s（可先 ls 查看 id 或 FR 编号）" % tid)


def audit(action, detail):
    log_path = Path(CONF["ops_log"])
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write("%s | %s | %s | %s\n" % (stamp, CONF["user"], action, detail))
    except Exception as e:
        out("# 警告: 审计日志写入失败: %s" % e)


def user_id(conf):
    users = rpc("getAllUsers", {}, conf) or []
    for u in users:
        if u["username"] == conf["user"]:
            return u["id"]
    return None


def print_task_row(t, colmap):
    ref = "[" + t["reference"] + "] " if t.get("reference") else ""
    title = (t.get("title") or "").replace("\n", " ")
    out("Task #%s  |  %s  |  %s%s" % (t["id"], colmap.get(t.get("column_id"), "?"), ref, title))


def cmd_ls(args):
    pid = project_id(CONF)
    colmap = col_title_map(pid, CONF)
    rows = []
    for t in all_tasks(pid, CONF):
        if args.all or t.get("is_active"):
            rows.append((colmap.get(t.get("column_id"), "?"), t))
    for _, t in sorted(rows, key=lambda x: (x[1]["column_id"], x[1]["position"])):
        print_task_row(t, colmap)
    out("# %d 张卡（项目 %s）" % (len(rows), CONF["project"]))


def cmd_open(args):
    pid = project_id(CONF)
    colmap = col_title_map(pid, CONF)
    n = 0
    for _, t in sorted(((colmap.get(t.get("column_id"), "?"), t) for t in all_tasks(pid, CONF) if t.get("is_active")),
                       key=lambda x: (x[1]["column_id"], x[1]["position"])):
        print_task_row(t, colmap)
        n += 1
    out("# 未完成 %d 张" % n)


def cmd_get(args):
    pid = project_id(CONF)
    colmap = col_title_map(pid, CONF)
    t = find_task(args.task, pid, CONF, colmap)
    out("Task #%s  %s%s" % (t["id"], ("[" + t["reference"] + "] ") if t.get("reference") else "", t.get("title") or ""))
    out("  列: %s" % colmap.get(t.get("column_id"), "?"))
    out("  描述: %s" % (t.get("description") or "(无)"))
    for cm in rpc("getAllComments", {"task_id": t["id"]}, CONF) or []:
        who = cm.get("username") or cm.get("name") or cm.get("user_id", "?")
        out("  评论[%s] %s: %s" % (who, cm.get("date_creation") or "", (cm.get("comment") or "").replace("\n", " ")))
    if t.get("date_due"):
        out("  截止: %s" % t["date_due"])
    if t.get("tags"):
        out("  标签: %s" % ", ".join(x.get("name", "") for x in t["tags"]))
    out("  状态: %s" % ("未完成(开启)" if t.get("is_active") else "已关闭"))


def cmd_by_fr(args):
    cmd_get(argparse.Namespace(task=args.fr))


def cmd_create(args):
    if args.dry_run:
        out("# [dry-run] 将建卡: %s" % args.title)
        return
    pid = project_id(CONF)
    col_id = resolve_column(pid, args.col, CONF) if args.col else None
    params = {
        "project_id": pid,
        "title": args.title,
        "description": args.desc or "",
        "column_id": col_id if col_id is not None else 1,
        "reference": args.fr or "",
    }
    try:
        new_id = rpc("createTask", params, CONF)
    except RuntimeError as e:
        # reference 可能撞卡：把 FR 放标题，正文留空 reference
        if args.fr and "reference" in str(e):
            params.pop("reference", None)
            new_id = rpc("createTask", params, CONF)
            audit("create", "project=%s task=%s fr=%s(REF冲突,放标题)" % (CONF["project"], new_id, args.fr))
        else:
            raise
    audit("create", "project=%s title=%s fr=%s col=%s -> task=%s" % (CONF["project"], args.title, args.fr, args.col, new_id))
    out("已建卡 Task #%s%s" % (new_id, (" [%s]" % args.fr) if args.fr else ""))


def cmd_move(args):
    pid = project_id(CONF)
    colmap = col_title_map(pid, CONF)
    t = find_task(args.task, pid, CONF, colmap)
    if args.dry_run:
        out("# [dry-run] 将把 Task #%s 从 %s 移到 %s" % (t["id"], colmap.get(t["column_id"]), args.col))
        return
    col_id = resolve_column(pid, args.col, CONF)
    if t.get("column_id") == col_id:
        out("Task #%s 已在 %s，无需移动" % (t["id"], args.col))
    else:
        tasks_in_col = [x for x in all_tasks(pid, CONF) if x.get("column_id") == col_id and x.get("is_active")]
        pos = len(tasks_in_col) + 1
        rpc("moveTaskPosition", {"project_id": pid, "task_id": t["id"], "column_id": col_id, "position": pos, "swimlane_id": 0}, CONF)
        audit("move", "task=%s %s -> %s" % (t["id"], colmap.get(t.get("column_id")), args.col))
        out("已移动 Task #%s 到 %s" % (t["id"], args.col))
    if args.comment:
        rpc("createComment", {"task_id": t["id"], "user_id": user_id(CONF), "content": args.comment}, CONF)
        audit("comment", "task=%s comment=%s" % (t["id"], args.comment))
        out("  已加评论")


def cmd_comment(args):
    pid = project_id(CONF)
    colmap = col_title_map(pid, CONF)
    t = find_task(args.task, pid, CONF, colmap)
    if args.dry_run:
        out("# [dry-run] 将给 Task #%s 加评论: %s" % (t["id"], args.message))
        return
    rpc("createComment", {"task_id": t["id"], "user_id": user_id(CONF), "content": args.message}, CONF)
    audit("comment", "task=%s comment=%s" % (t["id"], args.message))
    out("已给 Task #%s 加评论" % t["id"])


def cmd_log(args):
    log_path = Path(CONF["ops_log"])
    if not log_path.exists():
        out("(暂无操作日志)")
        return
    lines = log_path.read_text(encoding="utf-8").splitlines()
    tail = lines[-max(1, args.n):]
    for ln in tail:
        out(ln)
    out("# 共 %d 条，最近 %d 条" % (len(lines), len(tail)))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(prog="kb", description="Kanboard JSON-RPC CLI（pm-bot）")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps_ls = sub.add_parser("ls", help="列出项目全部卡")
    ps_ls.add_argument("-p", "--project")
    ps_ls.add_argument("--all", action="store_true", help="含已完成")
    ps_ls.set_defaults(func=cmd_ls)

    ps_open = sub.add_parser("open", help="列出未完成卡")
    ps_open.add_argument("-p", "--project")
    ps_open.set_defaults(func=cmd_open)

    ps_get = sub.add_parser("get", help="查看卡详情")
    ps_get.add_argument("task", help="任务 id 或 FR 编号")
    ps_get.set_defaults(func=cmd_get)

    ps_fr = sub.add_parser("by-fr", help="按 FR 编号查卡")
    ps_fr.add_argument("fr")
    ps_fr.set_defaults(func=cmd_by_fr)

    ps_c = sub.add_parser("create", help="建卡")
    ps_c.add_argument("-t", "--title", required=True)
    ps_c.add_argument("-p", "--project")
    ps_c.add_argument("--fr", help="FR 编号，写入 reference 字段")
    ps_c.add_argument("--desc")
    ps_c.add_argument("--col")
    ps_c.add_argument("--dry-run", action="store_true")
    ps_c.set_defaults(func=cmd_create)

    ps_m = sub.add_parser("move", help="移动卡到列")
    ps_m.add_argument("task")
    ps_m.add_argument("-c", "--col", required=True)
    ps_m.add_argument("--comment")
    ps_m.add_argument("--dry-run", action="store_true")
    ps_m.set_defaults(func=cmd_move)

    ps_cm = sub.add_parser("comment", help="给卡加评论")
    ps_cm.add_argument("task")
    ps_cm.add_argument("-m", "--message", required=True)
    ps_cm.add_argument("--dry-run", action="store_true")
    ps_cm.set_defaults(func=cmd_comment)

    ps_log = sub.add_parser("log", help="查看审计日志")
    ps_log.add_argument("-n", type=int, default=10)
    ps_log.set_defaults(func=cmd_log)

    args = p.parse_args()
    try:
        args.func(args)
    except RuntimeError as e:
        out("错误: %s" % e)
        sys.exit(1)


if __name__ == "__main__":
    main()
