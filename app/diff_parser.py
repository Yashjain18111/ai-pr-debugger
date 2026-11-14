"""
Git diff and patch parser for AI PR Debugger.
Extracts modified files, hunks, and line number contexts from unified diffs.
"""

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

EXCLUDED_EXTENSIONS = {
    ".lock", ".min.js", ".min.css", ".map", ".png", ".jpg", ".jpeg",
    ".gif", ".svg", ".ico", ".pdf", ".pyc", ".pyd", ".so", ".dll"
}

EXCLUDED_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Pipfile.lock", "uv.lock", "Cargo.lock", "composer.lock"
}


@dataclass
class DiffHunk:
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    lines: List[str] = field(default_factory=list)


@dataclass
class FileDiff:
    old_path: str
    new_path: str
    is_new: bool = False
    is_deleted: bool = False
    is_binary: bool = False
    hunks: List[DiffHunk] = field(default_factory=list)
    raw_diff: str = ""

    @property
    def file_path(self) -> str:
        return self.new_path if self.new_path != "/dev/null" else self.old_path

    @property
    def should_ignore(self) -> bool:
        filename = os.path.basename(self.file_path)
        if filename in EXCLUDED_FILES or self.is_binary:
            return True
        ext = os.path.splitext(filename)[1].lower()
        return ext in EXCLUDED_EXTENSIONS


def parse_unified_diff(diff_text: str) -> List[FileDiff]:
    """Parse a unified git diff into structured FileDiff objects."""
    files: List[FileDiff] = []
    current_file: Optional[FileDiff] = None
    current_hunk: Optional[DiffHunk] = None
    raw_lines: List[str] = []

    diff_file_pattern = re.compile(r"^diff --git a/(.*) b/(.*)$")
    hunk_header_pattern = re.compile(
        r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
    )

    for line in diff_text.splitlines():
        file_match = diff_file_pattern.match(line)
        if file_match:
            if current_file:
                current_file.raw_diff = "\n".join(raw_lines)
                files.append(current_file)
                raw_lines = []
            old_path, new_path = file_match.group(1), file_match.group(2)
            current_file = FileDiff(old_path=old_path, new_path=new_path)
            current_hunk = None
            raw_lines.append(line)
            continue

        if current_file:
            raw_lines.append(line)
            if line.startswith("new file mode"):
                current_file.is_new = True
            elif line.startswith("deleted file mode"):
                current_file.is_deleted = True
            elif "Binary files" in line:
                current_file.is_binary = True

            hunk_match = hunk_header_pattern.match(line)
            if hunk_match:
                old_start = int(hunk_match.group(1))
                old_len = int(hunk_match.group(2) or 1)
                new_start = int(hunk_match.group(3))
                new_len = int(hunk_match.group(4) or 1)
                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_length=old_len,
                    new_start=new_start,
                    new_length=new_len
                )
                current_file.hunks.append(current_hunk)
            elif current_hunk is not None:
                current_hunk.lines.append(line)

    if current_file:
        current_file.raw_diff = "\n".join(raw_lines)
        files.append(current_file)

    return files


def get_git_diff(
    target_branch: Optional[str] = None,
    staged: bool = False,
    repo_path: str = "."
) -> str:
    """Retrieve git diff from current repository."""
    cmd = ["git", "-C", repo_path, "diff"]
    if staged:
        cmd.append("--staged")
    elif target_branch:
        cmd.append(f"{target_branch}...HEAD")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git diff execution failed: {e.stderr.strip()}")

