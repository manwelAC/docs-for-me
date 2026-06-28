from pathlib import Path


RESPONSE_RULES = """You are writing a programmer-friendly guide, not modifying the repository.
Do not create, edit, rename, or delete files.
Do not ask a follow-up question.
Return the documentation directly in Markdown.
Use clear, plain language. Keep it useful for a developer who wants to quickly understand what is here and what it does.
Do not include risk sections, editing notes, audit notes, or security review language."""


def build_file_prompt(path: Path, language: str, content: str, structure: list[str]) -> str:
    structure_text = "\n".join(f"- {item}" for item in structure) or "- No structure detected."
    return f"""{RESPONSE_RULES}

Write clear developer documentation for this exact file.

File: {path}
Language: {language}

Detected structure:
{structure_text}

Explain:
- what this file does
- what is inside it
- how a programmer should understand its role
- important visible labels, data concepts, endpoints, and dependencies when visible
- a short reading guide for where to look first

File content:
```{language.lower()}
{content}
```
"""


def build_folder_prompt(path: Path, files: list) -> str:
    file_list = "\n".join(f"- {item.relative_path} ({item.size} bytes)" for item in files)
    return f"""{RESPONSE_RULES}

Write clear developer documentation for this exact folder.
Folder: {path}

Files:
{file_list}

Explain:
- what this folder appears to contain
- the main areas inside it
- important files and their role in the folder
- how files connect to routes, APIs, models, services, UI, data, or other dependencies
- how the parts fit together as a developer-readable system map
- where a programmer should start reading

Do not include raw source code or code blocks. Describe roles and connections in words.
"""


def build_changes_prompt(diff: str, staged: bool, since: str | None) -> str:
    mode = f"changes since {since}" if since else "staged changes" if staged else "unstaged changes"
    return f"""{RESPONSE_RULES}

Explain these Git changes for a developer.
Mode: {mode}

Include:
- a "Summary" section that explains the main changed flow in plain language
- a "What Changed" section that describes each changed file in words a programmer can understand
- a "Changed Areas" section that groups related file changes into user/developer-facing flows
- changed functions, methods, or important code areas when visible
- a "Commit Message" section with one copy-paste-ready commit message in a text code block. Use a precise subject line plus a short body that explains what should be committed, which flow changed, and which files or areas are involved
- a "Files Checked" section
- an "Accuracy Note" section at the end with this exact note:
  "This guide is generated from the Git diff and may miss context that is only clear from running the app, reading related files, or knowing the intended behavior. Review the summary and commit message before committing."

Do not list raw code lines as evidence. Do not quote the diff unless absolutely necessary.
Explain what changed, what flow changed, which files were involved, and which functions or areas changed.

Diff:
```diff
{diff}
```
"""
