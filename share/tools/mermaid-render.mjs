#!/usr/bin/env node
/**
 * mermaid-render.mjs — mermaid 渲染器（复用 Playwright Chromium，零额外浏览器下载）
 *
 * 用法：
 *   node mermaid-render.mjs <input.mmd> [-o out.png] [--svg] [--scale 3]
 *                           [--bg white|transparent] [--preset ocean|none] [--help]
 *
 * 说明：
 *   - 自动探测 %LOCALAPPDATA%\ms-playwright\chromium-*\chrome-win64\chrome.exe（Playwright 升级换目录无感）
 *   - 生成临时 puppeteer 配置并设置 PUPPETEER_SKIP_DOWNLOAD=true
 *   - 优先使用 tools/mermaid/node_modules 下的本地 mermaid-cli；缺失则回退 npx（首次会下载）
 *   - --preset ocean 在文件未自带 %%{init}%% 时注入统一主题（微软雅黑 + Ocean 配色）
 */
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import os from "node:os";
import { basename, dirname, extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const TOOLS_DIR = dirname(fileURLToPath(import.meta.url));
const LOCAL_PKG_DIR = join(TOOLS_DIR, "mermaid", "node_modules", "@mermaid-js", "mermaid-cli");
const NPM_CLI = "11.17.0";

const PRESET_OCEAN =
  '%%{init: {"theme":"base","themeVariables":{"fontFamily":"Microsoft YaHei, sans-serif","fontSize":"20px","primaryColor":"#F3F7FA","primaryTextColor":"#2B3A4E","primaryBorderColor":"#065A82","lineColor":"#1C7293","secondaryColor":"#D6E7EF","tertiaryColor":"#FFFFFF","edgeLabelBackground":"#FFFFFF"}}}%%';

function usage() {
  console.log(`用法：node mermaid-render.mjs <input.mmd> [选项]

选项：
  -o, --out <path>       输出文件（默认：与输入同目录同名 .png；--svg 时 .svg）
      --svg              输出 SVG（默认 PNG）
      --scale <n>        缩放倍数（默认 3）
      --bg <white|transparent>  背景（默认 white）
      --preset <ocean|none>     主题预设（默认 ocean；文件已含 %%{init}%% 时不覆盖）
  -h, --help             显示本帮助`);
}

function parseArgs(argv) {
  const opts = { input: null, out: null, svg: false, scale: "3", bg: "white", preset: "ocean" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-h" || a === "--help") return { help: true };
    if (a === "-o" || a === "--out") { opts.out = argv[++i]; continue; }
    if (a === "--svg") { opts.svg = true; continue; }
    if (a === "--scale") { opts.scale = argv[++i]; continue; }
    if (a === "--bg") { opts.bg = argv[++i]; continue; }
    if (a === "--preset") { opts.preset = argv[++i]; continue; }
    if (a.startsWith("-")) throw new Error(`未知参数：${a}`);
    if (!opts.input) { opts.input = a; continue; }
    throw new Error(`多余参数：${a}`);
  }
  if (!opts.input) throw new Error("缺少输入文件（.mmd）");
  return opts;
}

function findChromium() {
  const root = join(os.homedir(), "AppData", "Local", "ms-playwright");
  if (!existsSync(root)) return null;
  const byVersion = (a, b) => Number(a.split("-").pop()) - Number(b.split("-").pop());
  const full = readdirSync(root).filter((d) => /^chromium-\d+$/.test(d)).sort(byVersion).reverse();
  for (const d of full) {
    const exe = join(root, d, "chrome-win64", "chrome.exe");
    if (existsSync(exe)) return exe;
  }
  const shell = readdirSync(root)
    .filter((d) => /^chromium_headless_shell-\d+$/.test(d))
    .sort(byVersion)
    .reverse();
  for (const d of shell) {
    const exe = join(root, d, "chrome-headless-shell-win64", "chrome-headless-shell.exe");
    if (existsSync(exe)) return exe;
  }
  return null;
}

function localMmdcJs() {
  const pkg = join(LOCAL_PKG_DIR, "package.json");
  if (!existsSync(pkg)) return null;
  try {
    const bin = JSON.parse(readFileSync(pkg, "utf8")).bin;
    const rel = typeof bin === "string" ? bin : bin && bin.mmdc;
    if (!rel) return null;
    const js = join(LOCAL_PKG_DIR, rel);
    return existsSync(js) ? js : null;
  } catch {
    return null;
  }
}

function npxCliJs() {
  const js = join(dirname(process.execPath), "node_modules", "npm", "bin", "npx-cli.js");
  return existsSync(js) ? js : null;
}

function pngSize(buf) {
  if (buf.length < 24 || buf.readUInt32BE(0) !== 0x89504e47) return null;
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

function svgSize(text) {
  const w = /width="([\d.]+)/.exec(text);
  const h = /height="([\d.]+)/.exec(text);
  return w && h ? { width: Math.round(Number(w[1])), height: Math.round(Number(h[1])) } : null;
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) return usage();

  const input = resolve(opts.input);
  if (!existsSync(input)) throw new Error(`输入文件不存在：${input}`);
  if (extname(input).toLowerCase() !== ".mmd") throw new Error(`输入必须是 .mmd：${input}`);

  const out = resolve(
    opts.out || join(dirname(input), basename(input, extname(input)) + (opts.svg ? ".svg" : ".png")),
  );
  mkdirSync(dirname(out), { recursive: true });

  const chromium = findChromium();
  if (!chromium) {
    throw new Error(
      "未找到 Playwright Chromium。请先运行：npx playwright install chromium\n" +
        "（或设置 PUPPETEER_EXECUTABLE_PATH 指向可用 Chrome）",
    );
  }

  const tmpDir = join(os.tmpdir(), `mermaid-render-${process.pid}`);
  mkdirSync(tmpDir, { recursive: true });
  const cfgPath = join(tmpDir, "pptr.json");
  const mmdPath = join(tmpDir, "input.mmd");
  writeFileSync(
    cfgPath,
    JSON.stringify({ executablePath: chromium, args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"] }),
    "utf8",
  );

  let source = readFileSync(input, "utf8");
  if (opts.preset !== "none" && !source.trimStart().startsWith("%%{init")) {
    if (opts.preset !== "ocean") throw new Error(`未知预设：${opts.preset}（可选 ocean|none）`);
    source = PRESET_OCEAN + "\n" + source;
  }
  writeFileSync(mmdPath, source, "utf8");

  const mmdcArgs = ["-i", mmdPath, "-o", out, "-p", cfgPath, "-b", opts.bg, "-s", String(opts.scale)];
  const env = { ...process.env, PUPPETEER_SKIP_DOWNLOAD: "true" };
  const localJs = localMmdcJs();
  let result;
  if (localJs) {
    result = spawnSync(process.execPath, [localJs, ...mmdcArgs], { stdio: "inherit", env });
  } else {
    const npxJs = npxCliJs();
    const npxArgs = ["--yes", `@mermaid-js/mermaid-cli@${NPM_CLI}`, ...mmdcArgs];
    if (npxJs) {
      result = spawnSync(process.execPath, [npxJs, ...npxArgs], { stdio: "inherit", env });
    } else {
      result = spawnSync("npx.cmd", npxArgs, { stdio: "inherit", env, shell: true });
    }
  }
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`mermaid-cli 退出码 ${result.status}`);

  const buf = readFileSync(out);
  const size = opts.svg ? svgSize(buf.toString("utf8")) : pngSize(buf);
  console.log(`\n输出：${out}`);
  if (size) {
    const ratio = (size.height / size.width).toFixed(3);
    console.log(`尺寸：${size.width} x ${size.height}（高/宽 = ${ratio}）`);
  }
  rmSync(tmpDir, { recursive: true, force: true });
}

try {
  main();
} catch (e) {
  console.error(`mermaid-render 失败：${e.message}`);
  process.exit(1);
}
