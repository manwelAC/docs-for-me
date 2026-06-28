from docs_for_me.prompts import build_changes_prompt


def test_changes_prompt_requires_accuracy_note_and_commit_message() -> None:
    prompt = build_changes_prompt("diff --git a/a.py b/a.py", staged=False, since=None)

    assert '"Accuracy Note" section' in prompt
    assert "copy-paste-ready commit message" in prompt
    assert "Do not list raw code lines as evidence" in prompt
    assert "which functions or areas changed" in prompt
