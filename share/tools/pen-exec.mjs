#!/usr/bin/env node
// pen-exec: drive the pen.dev CLI headless design engine from opencode.
// Your opencode model (deepseek, etc.) is the designer; pen is only the engine.
// No Claude / Gemini / Codex sub-agent is involved.
//
// The engine is started per invocation ("pen interactive" in headless mode).
// It re-opens the same .pen file each time (-i), applies the commands, save()s,
// and exits. Use ONE execute() per invocation for unambiguous results, or batch
// a few small commands at once.
//
// Usage:
//   node pen-exec.mjs --file <out.pen> --cmd "execute({...})"
//   node pen-exec.mjs --file <out.pen> --cmds-file <cmds.txt>
//   node pen-exec.mjs --dump-skill <dir>            # save read_skill() docs
//
// Auth is read from PEN_CLI_KEY or a stored `pen login`, same as the pen CLI.

import { spawn, spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const NPM = process.platform === "win32" ? "npm.cmd" : "npm";

function penEntry() {
  // Single command string avoids Node's DEP0190 (args + shell:true) warning.
  const r = spawnSync(`${NPM} root -g`, { encoding: "utf8", shell: true });
  const root = (r.stdout || "").trim().replace(/\r?\n$/, "");
  return join(root, "@pen.dev", "cli", "dist", "index.mjs");
}

function stripAnsi(s) {
  return s.replace(/\u001b\[[0-9;]*m/g, "").replace(/\r/g, "");
}

function parseArgs(argv) {
  const o = { cmds: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--file") o.file = argv[++i];
    else if (a === "--cmd") o.cmds.push(argv[++i]);
    else if (a === "--cmds-file") o.cmdsFile = argv[++i];
    else if (a === "--dump-skill") o.dumpSkill = argv[++i];
    else if (a === "--clean") o.clean = true;
    else {
      console.error(`unknown arg: ${a}`);
      process.exit(2);
    }
  }
  return o;
}

function runSession(file, commands) {
  return new Promise((resolve) => {
    const args = ["interactive"];
    if (file && existsSync(file)) args.push("-i", file);
    if (file) args.push("-o", file);
    const child = spawn(process.execPath, [penEntry(), ...args], {
      stdio: ["pipe", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.stderr.on("data", (d) => (stderr += d));
    const input = [...commands, "save()", "exit()"].join("\n") + "\n";
    child.stdin.write(input);
    child.stdin.end();
    child.on("close", (code) =>
      resolve({ code, stdout: stripAnsi(stdout), stderr: stripAnsi(stderr) })
    );
  });
}

// First "pen > " marker introduces the first command's result. Everything after
// it is the transcript we want (banner removed). Drop the trailing save/exit noise.
function cleanTranscript(stdout) {
  const idx = stdout.indexOf("pen > ");
  let body = idx >= 0 ? stdout.slice(idx + "pen > ".length) : stdout;
  body = body
    .split("\n")
    .filter((l) => l.trim() !== "" && !/^Saved /.test(l) && l.trim() !== "Goodbye.")
    .join("\n");
  return body.trim();
}

async function dumpSkill(dir) {
  mkdirSync(dir, { recursive: true });
  const scratch = join(dir, ".scratch.pen");
  const rootRes = await runSession(scratch, ["read_skill()"]);
  writeFileSync(join(dir, "SKILL.md"), cleanTranscript(rootRes.stdout), "utf8");
  const rootBody = cleanTranscript(rootRes.stdout);
  const refs = [...rootBody.matchAll(/read_skill\(\{\s*path:\s*"([^"]+)"\s*\}\)/g)].map((m) => m[1]);
  const want = [...new Set(["pen-schema.md", "execute.md", ...refs])];
  for (const p of want) {
    const safe = p.replace(/[^a-zA-Z0-9._-]/g, "_");
    const r = await runSession(scratch, [`read_skill({ path: "${p}" })`]);
    const txt = cleanTranscript(r.stdout);
    writeFileSync(join(dir, safe), txt, "utf8");
    console.error(`wrote ${safe} (${txt.length} chars)`);
  }
  console.error(`dumped skill docs into ${dir}`);
}

const opts = parseArgs(process.argv.slice(2));

if (opts.dumpSkill) {
  await dumpSkill(opts.dumpSkill);
  process.exit(0);
}

if (!opts.file) {
  console.error("--file <out.pen> is required");
  process.exit(2);
}

const cmds =
  opts.cmdsFile && existsSync(opts.cmdsFile)
    ? readFileSync(opts.cmdsFile, "utf8")
        .split(/\r?\n/)
        .map((l) => l.trim())
        .filter((l) => l && !l.startsWith("#"))
    : opts.cmds;

if (cmds.length === 0) {
  console.error("no commands provided (--cmd or --cmds-file)");
  process.exit(2);
}

const { code, stdout, stderr } = await runSession(opts.file, cmds);
process.stdout.write(opts.clean ? cleanTranscript(stdout) : stdout);
if (stderr.trim()) process.stdout.write("\n[stderr]\n" + stderr.trim());
process.exit(code === 0 ? 0 : 1);
