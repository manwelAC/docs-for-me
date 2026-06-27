<p align="center">
  <img src="https://i.pinimg.com/736x/7a/6d/a5/7a6da5d2962db34846138e08e2932f01.jpg" alt="docs-for-me logo" width="220">
</p>

<h1 align="center">docs-for-me</h1>

<p align="center">
  A CLI that creates programmer-friendly guides for files, folders, and Git changes.
</p>

It is meant for the everyday developer moment where you want to know:

- What is in this file?
- What does this folder contain?
- What did I change before I commit?
- What commit message can I copy after reviewing the changes?

The output is Markdown, so it can be read in a terminal, saved beside a project,
or deleted after review.

## Install

Install it with npm:

```powershell
npm install -g docs-for-me
```

Then run it anywhere:

```powershell
docs-for-me --help
docs-for-me changes --ai none --out changes-guide.md
```

You can also install it inside one project:

```powershell
npm install --save-dev docs-for-me
npm exec docs-for-me changes --ai none --out changes-guide.md
```

For a one-time trial without installing globally:

```powershell
npx docs-for-me --help
```

Important: `npx docs-for-me` runs the package once. It does not permanently add
`docs-for-me` as a command. If you want to type `docs-for-me ...` directly,
install it globally with `npm install -g docs-for-me`.

Users do not need to install Python, pip, or pipx.

The first npm release ships with a bundled Windows x64 executable. macOS and
Linux builds can be added after the Windows release flow is stable.

## What It Does

`docs-for-me` supports three main tasks:

```bash
docs-for-me file <path>
docs-for-me folder <path>
docs-for-me changes
```

It has two modes:

- `--ai none` uses local static analysis and Git diff parsing.
- `--ai opencode` asks OpenCode to write a fuller guide.

Static mode is useful when you want quick local output. OpenCode mode is useful
when you want a more natural explanation.

## Basic Usage

Document one file:

```powershell
docs-for-me file "app/(dashboard)/bookings/page.tsx" --ai none --out bookings-doc.md
```

Document one folder:

```powershell
docs-for-me folder app --ai none --out app-docs.md
```

Explain unstaged Git changes:

```powershell
docs-for-me changes --ai none --out changes-guide.md
```

Explain staged Git changes:

```powershell
docs-for-me changes --staged --ai none --out changes-guide.md
```

Compare changes since a branch or ref:

```powershell
docs-for-me changes --since main --ai none --out changes-guide.md
```

## OpenCode Mode

OpenCode mode uses the `opencode` CLI as the AI provider.

First, make sure OpenCode works:

```powershell
opencode run "Say hello in one sentence."
```

Then run:

```powershell
docs-for-me file "app/(dashboard)/bookings/page.tsx" --ai opencode --out bookings-ai-doc.md
```

Or for Git changes:

```powershell
docs-for-me changes --ai opencode --out changes-ai-guide.md
```

When OpenCode is working, the generated Markdown should not contain:

```markdown
- **AI:** unavailable or disabled (`opencode`)
```

## Contributor Setup

The core CLI is written in Python, but npm is the user-facing package path.
Use this setup only when developing `docs-for-me` itself:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e . pytest
pytest
```

To build the Windows executable that the npm package runs:

```powershell
npm run build:exe:win
```

Then test the npm wrapper locally:

```powershell
npm run test:npm-local
```

The npm wrapper expects the executable here:

```text
prebuilt/win32-x64/docs-for-me.exe
```

When publishing to npm, that executable is included so users can run
`docs-for-me ...` after `npm install -g docs-for-me` without setting up Python.

If that line appears, `docs-for-me` fell back to static mode.

## Git Changes Guide

The `changes` command is designed for pre-commit review. It summarizes the diff,
lists changed files, explains what the changes appear to do, and includes a
copy-paste-ready commit message.

Example output includes:

```text
update: search behavior and plan limits
```

Review the generated guide before committing. The guide is meant to save time,
not replace your own final check.

## Progress Messages

Commands print progress messages so long-running AI calls do not look frozen:

```text
[  0.0s] Reading file: app/(dashboard)/bookings/page.tsx
[  0.0s] Preparing documentation with provider: opencode
[  0.0s] Waiting for AI response. This can take a moment...
[  5.0s] OpenCode is reading the file and prompt...
[ 10.0s] OpenCode is drafting the guide...
```

Hide progress messages with:

```powershell
docs-for-me file README.md --quiet
```

## Privacy

`--ai none` runs locally and does not call an AI provider.

`--ai opencode` sends the relevant file contents or Git diff to OpenCode and to
whatever model/provider OpenCode is configured to use. Do not use AI mode on
private or sensitive code unless you are comfortable with that provider handling
the content.

## Current Provider Support

Today:

- `none`
- `opencode`

The code is provider-based, so more providers can be added later.

## Project Status

`docs-for-me` is early-stage. It is published on npm for Windows x64 first.

Good next steps:

- add config file support
- add more AI providers
- add macOS and Linux npm builds
