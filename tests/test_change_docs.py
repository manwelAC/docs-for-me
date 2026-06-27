from docs_for_me.git.change_docs import _fallback_changes_doc


def test_fallback_changes_doc_includes_commit_message() -> None:
    diff = """
diff --git a/app/bookings/page.tsx b/app/bookings/page.tsx
index 111..222 100644
--- a/app/bookings/page.tsx
+++ b/app/bookings/page.tsx
@@ -1 +1,2 @@
+const title = "Bookings"
"""

    markdown = _fallback_changes_doc(diff, "none", staged=False, since=None)

    assert "## Commit Message" in markdown
    assert "## What Changed" in markdown
    assert "## Accuracy Note" in markdown
    assert "```text" in markdown
    assert "bookings" in markdown
    assert "Text or value: `Bookings`" in markdown


def test_fallback_changes_doc_detects_search_commit_theme() -> None:
    diff = """
diff --git a/app/(dashboard)/bookings/page.tsx b/app/(dashboard)/bookings/page.tsx
index 111..222 100644
--- a/app/(dashboard)/bookings/page.tsx
+++ b/app/(dashboard)/bookings/page.tsx
@@ -1,3 +1,6 @@
+const [searchInput, setSearchInput] = useState("");
+onKeyDown={(event) => event.key === "Enter" && setSearch(searchInput.trim())}
-value={search}
+value={searchInput}
diff --git a/app/(dashboard)/guests/page.tsx b/app/(dashboard)/guests/page.tsx
index 333..444 100644
--- a/app/(dashboard)/guests/page.tsx
+++ b/app/(dashboard)/guests/page.tsx
@@ -1,3 +1,6 @@
+const [searchInput, setSearchInput] = useState("");
+onKeyDown={(event) => event.key === "Enter" && setSearch(searchInput.trim())}
-value={search}
+value={searchInput}
"""

    markdown = _fallback_changes_doc(diff, "none", staged=False, since=None)

    assert "typed search text" in markdown
    assert "apply search with Enter" in markdown
    assert "update: search behavior" in markdown
    assert "Evidence from added or updated lines" in markdown
