from pathlib import Path

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
    assert "## Changed Areas" in markdown
    assert "## Accuracy Note" in markdown
    assert "```text" in markdown
    assert "Added:" in markdown
    assert "Affected files:" in markdown
    assert "Diff size:" in markdown
    assert "bookings" in markdown
    assert "Evidence from added or updated lines" not in markdown


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

    assert "separates typing from applying the value" in markdown
    assert "explicit action" in markdown
    assert "update: apply input changes through an explicit action" in markdown
    assert "Updated:" in markdown
    assert "- bookings and guests: input is now applied through an explicit action instead of changing results immediately." in markdown
    assert "Evidence from added or updated lines" not in markdown


def test_fallback_changes_doc_summarizes_branch_filter_flow() -> None:
    diff = """
diff --git a/app/Http/Controllers/ExpensesReportController.php b/app/Http/Controllers/ExpensesReportController.php
index 111..222 100644
--- a/app/Http/Controllers/ExpensesReportController.php
+++ b/app/Http/Controllers/ExpensesReportController.php
@@ -1,6 +1,10 @@
-if ($branch_code !== 'all-branches') {
-    $query->where($branch_column, $user->branch_id);
-}
+if ($branch_code !== 'all-branches' && $branch_type === 'company') {
+    $query->whereIn($branch_column, $companyBranchCodes);
+}
+if ($branch_code !== 'all-branches' && $branch_type === 'franchise') {
+    $query->whereIn($branch_column, $franchiseBranchCodes);
+}
"""

    markdown = _fallback_changes_doc(diff, "none", staged=False, since=None)

    assert "Filtering changed from direct single-value matching to grouped matching" in markdown
    assert "expenses report controller" in markdown
    assert "Evidence from added or updated lines" not in markdown
    assert "$query->whereIn" not in markdown
    assert "filtering now uses grouped matching instead of only direct matching" in markdown
    assert "update: support grouped filtering in expenses report controller" in markdown
    assert "Updated:" in markdown
    assert "- expenses report controller: filtering now uses grouped matching instead of only direct matching." in markdown


def test_fallback_changes_doc_avoids_vague_existing_behavior_summary() -> None:
    diff = """
diff --git a/app/Http/Controllers/AddProductController.php b/app/Http/Controllers/AddProductController.php
index 111..222 100644
--- a/app/Http/Controllers/AddProductController.php
+++ b/app/Http/Controllers/AddProductController.php
@@ -1,5 +1,7 @@
-function storeProduct() {
-    $query->where('branch_code', $user->branch_id);
-}
+function storeProduct() {
+    $query->whereIn('branch_code', $allowedBranchCodes);
+    $product->status = 'available';
+}
"""

    markdown = _fallback_changes_doc(diff, "none", staged=False, since=None)

    assert "updates existing behavior" not in markdown
    assert "add product controller" in markdown
    assert "filtering now uses grouped matching instead of only direct matching" in markdown
    assert "$query->whereIn" not in markdown
    assert "update: support grouped filtering in add product controller" in markdown
    assert "Updated:" in markdown
    assert "Visible changed areas: add product controller::storeProduct." in markdown


def test_change_checker_has_no_project_specific_analysis_terms() -> None:
    source = Path("src/docs_for_me/git/change_docs.py").read_text(encoding="utf-8").lower()

    for term in [
        "branch",
        "company",
        "franchise",
        "booking",
        "guest",
        "hotel",
        "payment",
        "expense",
        "product",
    ]:
        assert term not in source
