<p align="center">
  <img src="https://i.pinimg.com/736x/7a/6d/a5/7a6da5d2962db34846138e08e2932f01.jpg" alt="docs-for-me logo" width="220">
</p>

<h1 align="center">docs-for-me</h1>

<p align="center">
  A CLI that turns Git changes into programmer-friendly review guides and commit-ready messages.
</p>

`docs-for-me` is built for the everyday developer moment right before a commit:

- What did I change?
- What files and flows were affected?
- What should the commit message say?
- What can I paste into `git commit` after I review it?

The output is Markdown, so it can be read in a terminal, saved beside a project,
or deleted after review.

## Install

Install it with npm:

```powershell
npm install -g docs-for-me
```

Then run it inside a Git repository:

```powershell
docs-for-me changes --ai none --out changes-guide.md
```

You can also install it inside one project:

```powershell
npm install --save-dev docs-for-me
npm exec docs-for-me changes --ai none --out changes-guide.md
```

For a one-time trial without installing globally:

```powershell
npx docs-for-me changes --ai none --out changes-guide.md
```

## Usage

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

## What It Gives You

The `changes` command reads your Git diff and writes a Markdown guide with:

- a plain-language summary
- changed files and changed areas
- changed functions or code areas when visible
- a copy-paste-ready commit message
- a files-checked list
- an accuracy note

## OpenCode Mode

OpenCode mode uses the `opencode` CLI as the AI provider.

First, make sure OpenCode works:

```powershell
opencode run "Say hello in one sentence."
```

Then run:

```powershell
docs-for-me changes --ai opencode --out changes-ai-guide.md
```

When OpenCode is working, the generated Markdown should not contain:

```markdown
- **AI:** unavailable or disabled (`opencode`)
```

## Local vs AI Changes

`--ai none` does not use machine learning. It uses local diff parsing and
generic software detectors to describe visible change patterns.

`--ai opencode` sends the Git diff to OpenCode and asks it to produce the same
kind of guide with a more natural explanation and a subject-plus-body commit
message.

## Progress Messages

Commands print progress messages so long-running AI calls do not look frozen:

```text
[  0.0s] Reading Git diff for unstaged changes
[  0.0s] Preparing change guide with provider: none
[  0.0s] Reading Git diff...
[  0.0s] Parsing changed files and changed lines...
[  0.0s] Detected 42 changed line(s) across 3 file(s).
[  0.0s] Scoring 18 local detector signal(s)...
[  0.0s] Rendering developer-readable Markdown...
[  0.0s] Writing Markdown output
[  0.0s] Change guide ready.
```

Hide progress messages with:

```powershell
docs-for-me changes --ai none --quiet --out changes-guide.md
```

## Privacy

`--ai none` runs locally and does not call an AI provider.

`--ai opencode` sends your Git diff to OpenCode and to whatever model/provider
OpenCode is configured to use. Do not use AI mode on private or sensitive code
unless you are comfortable with that provider handling the content.

## Contributor Setup

The core CLI is written in Python, but npm is the user-facing package path.
Use this setup only when developing `docs-for-me` itself:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e . pytest
.venv\Scripts\python.exe -m pytest --basetemp .\build\pytest-temp
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
