<p align="center">
  <img src="https://i.pinimg.com/736x/7a/6d/a5/7a6da5d2962db34846138e08e2932f01.jpg" alt="docs-for-me logo" width="220">
</p>

<h1 align="center">docs-for-me</h1>

<p align="center">
  A CLI that turns Git changes into programmer-friendly review guides and commit-ready messages.
</p>

`docs-for-me` is built for the everyday developer moment right before a commit:

- What did I change before I commit?
- What files and flows were affected?
- What should the commit message say?
- What can I paste into `git commit` after I review it?

It can also create guides for specific files and folders, but the main workflow is
helping you understand Git changes without manually rereading every diff line.

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

`docs-for-me` supports three tasks:

```bash
docs-for-me changes
docs-for-me file <path>
docs-for-me folder <path>
```

The `changes` command is the main one. It reads your Git diff, explains the
change in plain language, groups related files, and writes a commit message you
can copy after reviewing.

It has two modes:

- `--ai none` uses local static analysis and Git diff parsing.
- `--ai opencode` asks OpenCode to write a fuller guide.

Static mode is useful when you want quick local output. OpenCode mode is useful
when you want a more natural explanation.

## Basic Usage

Create a pre-commit guide for unstaged changes:

```powershell
docs-for-me changes --ai none --out changes-guide.md
```

Create a guide for staged changes:

```powershell
docs-for-me changes --staged --ai none --out changes-guide.md
```

Compare changes since a branch or ref:

```powershell
docs-for-me changes --since main --ai none --out changes-guide.md
```

Use OpenCode for a more natural explanation:

```powershell
docs-for-me changes --ai opencode --out changes-ai-guide.md
```

Document one file:

```powershell
docs-for-me file "app/(dashboard)/bookings/page.tsx" --ai none --out bookings-doc.md
```

Document one folder:

```powershell
docs-for-me folder app --ai none --out app-docs.md
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

## Git Changes Guide

The `changes` command is designed for pre-commit review and commit-message prep.
It summarizes the diff, explains changed flows, groups related areas, lists the
files checked, and includes a copy-paste-ready commit message.

The commit message is intentionally more than a tiny one-line label. It includes
a subject plus a short body with categories such as `Added`, `Updated`,
`Refactored`, and `Removed` when those categories are visible from the diff.

Example commit message section:

```text
update: support grouped filtering in changed controllers

Updated:
- changed controllers: filtering now uses grouped matching instead of only direct matching.

Refactored:
- shared lookup files: related values now come from a shared lookup path.

Affected files: app/Http/Controllers/ExampleController.php, app/Services/ExampleService.php.

Visible changed areas: example controller::applyFilter, example service::resolveLookup.

Diff size: 2 file(s), 40 added line(s), 18 removed line(s).
```

Example commit command:

```powershell
git commit -m "update: support grouped filtering in changed controllers" -m "Updated: - changed controllers: filtering now uses grouped matching instead of only direct matching. Affected files: app/Http/Controllers/ExampleController.php. Diff size: 1 file(s), 20 added line(s), 8 removed line(s)."
```

Review the generated guide before committing. The guide is meant to save time,
not replace your own final check.

### Local vs AI Changes

`--ai none` does not use machine learning. It uses adaptive static analysis:
it reads the diff, detects general change patterns, derives names from files and
symbols, and builds the guide locally.

`--ai opencode` sends the Git diff to OpenCode and asks it to produce the same
kind of guide with a more natural explanation and a subject-plus-body commit
message. The OpenCode prompt is configured to include `Summary`, `What Changed`,
`Changed Areas`, `Commit Message`, `Files Checked`, and `Accuracy Note`.

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
