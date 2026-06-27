import shutil
import subprocess
import os
import re
import time

from docs_for_me.ai.base import AIProvider, AIResponse, ProgressCallback


class OpenCodeProvider(AIProvider):
    name = "opencode"

    def __init__(self, model: str | None = None) -> None:
        self.model = model

    def generate(
        self,
        prompt: str,
        files: list[str] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> AIResponse:
        executable = _find_opencode()
        if executable is None:
            return AIResponse(text="", used_ai=False)

        command = [executable, "run"]

        command.append(_compact_prompt_for_files(prompt) if files else prompt)

        for file_path in files or []:
            command.extend(["--file", file_path])

        if self.model:
            command.extend(["--model", self.model])

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            return AIResponse(text="", used_ai=False)

        stdout, stderr = _communicate_with_heartbeat(process, on_progress)

        if process.returncode != 0:
            return AIResponse(text="", used_ai=False)

        return AIResponse(text=_clean_output(stdout + "\n" + stderr), used_ai=True)


def _find_opencode() -> str | None:
    candidates = ["opencode.cmd", "opencode.exe", "opencode"]

    if os.name != "nt":
        candidates = ["opencode"]

    for candidate in candidates:
        executable = shutil.which(candidate)
        if executable:
            return executable

    return None


def _compact_prompt_for_files(prompt: str) -> str:
    if "Diff:\n```diff" in prompt:
        return (
            "Return a Markdown guide for the attached Git diff. "
            "Do not create files. Do not edit files. Do not ask questions. "
            "Explain what changed in plain language for programmers. "
            "Include these sections: Summary, What Changed, Commit Message, Files Checked, and Accuracy Note. "
            "The Commit Message section must contain one copy-paste-ready commit message inside a text code block. "
            "End with this exact Accuracy Note: "
            "\"This guide is generated from the Git diff and may miss context that is only clear from running the app, reading related files, or knowing the intended behavior. Review the summary and commit message before committing.\" "
            "Base the guide on the attached diff only."
        )

    if "Write clear developer documentation for this exact folder." in prompt:
        return (
            "Return Markdown documentation for the attached folder context. "
            "Do not create files. Do not edit files. Do not ask questions. "
            "Write it like a practical programmer guide, not an audit. "
            "Include these sections: Overview, What Is Inside, Main Areas, Important Files, How It Fits Together, and Reading Guide. "
            "Do not include Risks or Editing Notes. "
            "Base the documentation on the attached folder context only."
        )

    marker = "\nFile content:\n"
    if marker not in prompt:
        return prompt

    return (
        "Return Markdown documentation for the attached file. "
        "Do not create files. Do not edit files. Do not ask questions. "
        "Write it like a short programmer guide, not an audit. "
        "Include these sections: Overview, What Is Inside, What It Does, Important Parts, and Reading Guide. "
        "Do not include Risks or Editing Notes. Base the documentation on the attached file only."
    )


def _clean_output(output: str) -> str:
    text = re.sub(r"\x1b\[[0-9;]*m", "", output).strip()
    lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("> build"):
            continue
        if stripped.startswith("> "):
            continue
        lines.append(line.rstrip())

    return "\n".join(lines).strip()


def _communicate_with_heartbeat(
    process: subprocess.Popen[str],
    on_progress: ProgressCallback | None,
    interval_seconds: float = 5.0,
) -> tuple[str, str]:
    started_at = time.perf_counter()
    last_heartbeat = started_at
    messages = [
        "OpenCode is reading the file and prompt...",
        "OpenCode is drafting the guide...",
        "Still waiting for OpenCode...",
        "OpenCode is taking a little longer than usual...",
    ]
    message_index = 0

    while process.poll() is None:
        now = time.perf_counter()
        if on_progress and now - last_heartbeat >= interval_seconds:
            on_progress(messages[message_index % len(messages)])
            message_index += 1
            last_heartbeat = now
        time.sleep(0.2)

    stdout, stderr = process.communicate()
    return stdout or "", stderr or ""
