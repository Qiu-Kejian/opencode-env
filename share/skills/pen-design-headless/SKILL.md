---
name: pen-design-headless
description: >
  Generate or edit pen.dev `.pen` design files and export them to PNG/JPEG/WEBP/PDF
  headlessly, using the pen.dev CLI design engine driven directly by the current
  opencode model (no editor window, no Claude sub-agent). Use when the user wants a
  design/mockup/UI/slide/poster created or changed as a file, wants a design exported
  to an image, wants batch or scripted design generation, or when the live pen.dev
  editor (VS Code) is not open. Trigger on: "design me a...", "create a mockup",
  "make a .pen", "generate a landing page/app screen/dashboard/poster", "export this
  design to PNG". Do NOT use to edit a design that is already open in the pen.dev
  VS Code editor (use the `pencil` MCP tools for that live case).
---

# pen.dev Headless Design (opencode-native)

You (the opencode model, e.g. deepseek) are the **designer**. pen.dev is only the
**rendering/DSL engine**: it starts headless, applies your `execute()` snippets to a
`.pen` file, saves it, and can export images. No Claude/Gemini/Codex agent is involved.

Never run `pen --prompt ...` — that delegates to pen's own Claude agent and is not used here.

## 1. Prerequisites (check once)

Authentication is required by the headless engine (env `PEN_CLI_KEY`, or a prior
`pen login`). Verify:

```powershell
pen status
```

If it says `Not authenticated`, stop and tell the user to run `pen login` or set
`PEN_CLI_KEY`. Do not continue.

## 2. Load the pen.dev DSL before designing

Read the reference files (they teach the `.pen` schema, the `execute` API, and known pitfalls):

- `.opencode/skills/pen-design-headless/reference/execute.md`
- `.opencode/skills/pen-design-headless/reference/pen-schema.md`
- `.opencode/skills/pen-design-headless/reference/troubleshooting.md`（实战踩坑与自检清单，生成前必读）

Follow them strictly. pen.dev is **not** CSS/HTML: no `margin`, no percentage sizes,
no `alignItems: stretch/baseline`. Text needs an explicit `fill`. Set `name` on every
node. Use `layout`/`gap`/`padding`/`fill_container`/`fit_content` for structure.

## 3. Drive the engine with the helper

Helper: `.opencode/tools/pen-exec.mjs`

One call = one engine session: it opens the target `.pen` (creating it if absent),
runs your commands in order, saves, and prints the result transcript.

**Syntax rule (important):** each line in the commands file must be a
*interactive-shell tool call*, i.e. `execute({ input: '<javascript>' })`. Bare
JavaScript lines (`pos=FindEmptySpace(...)`) are rejected. Inside one `execute`
separate statements with `;` and keep it on a single line (one command per line).
`Get`, `Export`, `TakeScreenshot`, `SetVariables`, `Generate` etc. all run *inside*
`execute({ input: '...' })`; `save()`/`exit()` are added automatically by the helper.

- Single command (preferred; unambiguous output):

```powershell
node ".opencode/tools/pen-exec.mjs" --file "./designs/hero.pen" --cmd "f=Insert(document,{type:'frame',name:'Hero',layout:'vertical',gap:24,padding:64,width:1440,fill:'#0A0A0A'})" --clean
```

- Several commands (use a commands file to avoid shell quoting problems; one
  command per line, `#` lines are comments):

```powershell
node ".opencode/tools/pen-exec.mjs" --file "./designs/hero.pen" --cmds-file "./designs/_cmds.txt" --clean
```

Write the commands file with the Write tool when snippets contain quotes — never fight
the shell. `--clean` strips the startup banner.

### Recommended loop
1. Read the reference docs (section 2).
2. `execute` one section at a time (nav, hero, features, footer...). Keep each call
   focused. Globals (e.g. `f`, `navId`) persist only within a single session — to
   reuse an id in a later call, store it as a variable without `const`/`let` and run
   both calls in the same `--cmds-file`, or re-find it with `Get`.
3. Verify structure cheaply with `Get`/`Print` (e.g. layout problems via `ctx.problems`,
   or `Print(Get('<id>',{depth:1}))` to inspect the tree).
4. When a section is done, export it to a PNG:

```powershell
node ".opencode/tools/pen-exec.mjs" --file "./designs/hero.pen" --cmd "execute({ input: \"Export(['<frameId>'], 'png', './designs/exports')\" })" --clean
```
   Then:
   - **If your model can view images:** Read `./designs/exports/<frameId>.png` and
     fix visual issues you see.
   - **If your model is text-only (e.g. deepseek-v4-flash):** you cannot view the PNG.
     Verify with `Get`/`ctx.bounds`/`ctx.problems` (no collapsed/zero-size frames, no
     `partially clipped`/`fully clipped` problems, text has `fill`), then tell the user
     the PNG path and ask them to check it visually.

`TakeScreenshot()` attaches images only to pen's own agent session — in headless
scripting it is useless; always verify via `Export` (+ Read if multimodal).

## 4. Output conventions

- Save designs in the user's project, e.g. `./designs/<name>.pen` (never temp dirs).
- Export images into `./designs/exports/` and show the PNG to the user (Read it).
- Tell the user design generation takes a bit; keep them informed of progress.

## When NOT to use this skill

If the user is editing a design already open in the pen.dev editor inside VS Code,
use the live `pencil` MCP tools instead (real-time canvas edits, no file round-trip).
This headless skill is for generating/exporting files without an open editor.
