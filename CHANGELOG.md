# Changelog

All notable changes to `docs-for-me` will be documented in this file.

## 0.1.6 - 2026-06-28

- Remove npm postinstall output to avoid script-approval warnings during install.
- Keep the improved `docs-for-me --help` screen as the first-run guide.

## 0.1.5 - 2026-06-28

- Improve Git changes guides with subject-and-body commit messages.
- Add categorized commit message sections for added, updated, refactored, and removed changes when visible from the diff.
- Remove project-specific change analysis terms from the local changes checker.
- Refresh the top-level help screen around the Git changes workflow.
- Update README positioning to focus on pre-commit review and commit-message prep.

## 0.1.4 - 2026-06-27

- Improve the top-level help screen with a styled terminal UI.

## 0.1.3 - 2026-06-27

- Prepare npm release for adaptive large-folder summaries.
- Store temporary AI context files inside the project/folder so OpenCode can read them without external temp-directory permission errors.

## 0.1.2 - 2026-06-27

- Fix folder AI mode so OpenCode receives one generated folder-context attachment.
- Add test coverage for folder AI context generation.
- Add adaptive local folder summaries for larger folders.

## 0.1.1 - 2026-06-27

- Improve CLI help with direct `docs-for-me ...` examples after npm global install.
- Clarify that `npx docs-for-me` is only a one-time trial.
- Update README usage to match the npm package flow.

## 0.1.0 - 2026-06-27

- Add CLI commands for documenting files, folders, and Git changes.
- Add local static analysis mode with `--ai none`.
- Add OpenCode provider support with `--ai opencode`.
- Add progress messages and AI heartbeat updates.
- Add Git changes guide with copy-paste commit message.
- Add accuracy note for generated Git change guides.
