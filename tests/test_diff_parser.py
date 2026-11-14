from app.diff_parser import parse_unified_diff, EXCLUDED_FILES


SAMPLE_DIFF = """diff --git a/app/calculator.py b/app/calculator.py
index 1234567..89abcdef 100644
--- a/app/calculator.py
+++ b/app/calculator.py
@@ -1,3 +1,3 @@
 def calculate_total(price, quantity):
-    return price + quantity
+    return price * quantity
diff --git a/package-lock.json b/package-lock.json
index 1111111..2222222 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -1,2 +1,2 @@
 { "version": "1.0.0" }
"""


def test_parse_unified_diff_extracts_files_and_hunks():
    files = parse_unified_diff(SAMPLE_DIFF)
    assert len(files) == 2

    py_file = files[0]
    assert py_file.file_path == "app/calculator.py"
    assert len(py_file.hunks) == 1
    assert py_file.hunks[0].new_start == 1
    assert not py_file.should_ignore

    lock_file = files[1]
    assert lock_file.file_path == "package-lock.json"
    assert lock_file.should_ignore is True

