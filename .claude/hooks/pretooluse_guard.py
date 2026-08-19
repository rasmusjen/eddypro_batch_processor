#!/usr/bin/env python3
"""PreToolUse hook: block dangerous git operations and edits to protected data dirs.

Reads a JSON hook payload on stdin with `tool_name` and `tool_input`.
Exit 0 to allow. Exit 2 (with a stderr message) to block the tool call.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

# Directories that must never be written to or staged.
PROTECTED_DIR_PATTERNS = [
    r"(^|[/\\])data([/\\]|$)",
    r"(^|[/\\])logs([/\\]|$)",
    r"(^|[/\\])d:[/\\]l0_raw([/\\]|$)",
    r"(^|[/\\])d:[/\\]l1_processed([/\\]|$)",
]

PROTECTED_STAGE_PATTERNS = [
    r"(^|[/\\])data([/\\]|$)",
    r"(^|[/\\])logs([/\\]|$)",
    r"(^|[/\\])\.venv([/\\]|$)",
    r"(^|[/\\])venv([/\\]|$)",
    r"(^|[/\\])htmlcov([/\\]|$)",
]

EXACT_PROTECTED_STAGE_FILES = {
    "config/config.yaml",
    "config\\config.yaml",
    ".coverage",
    "coverage.xml",
}


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def split_commands(command: str) -> list[str]:
    """Split a shell command on &&, ;, and | into individual segments."""
    # Not a full shell parser, but good enough to catch chained dangerous
    # commands. Avoid splitting inside quotes where reasonably possible.
    parts = re.split(r"&&|\|\||;|\|", command)
    return [p.strip() for p in parts if p.strip()]


def current_branch() -> str | None:
    try:
        # nosec B603 B607 - fixed argv, no shell. Resolving git by PATH is
        # intentional so the hook works across platforms and installs.
        result = subprocess.run(  # noqa: S603, S607  # nosec B603 B607
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        return None
    return None


def tokens_of(segment: str) -> list[str]:
    return segment.split()


def is_git_subcommand(tokens: list[str], sub: str, index: int = 1) -> bool:
    return len(tokens) > index and tokens[0] == "git" and tokens[index] == sub


def check_git_push(tokens: list[str], segment: str) -> None:
    if not is_git_subcommand(tokens, "push"):
        return

    has_force = False
    has_force_with_lease = False
    for tok in tokens[2:]:
        if tok == "--force-with-lease" or tok.startswith("--force-with-lease="):
            has_force_with_lease = True
        elif tok in ("--force", "-f"):
            has_force = True

    # Determine push target (best-effort: look for main/master in args)
    targets_main = bool(re.search(r"\b(main|master)\b", segment))

    if has_force and not has_force_with_lease:
        block(
            "Blocked: 'git push --force'/'-f' is not allowed. "
            "Use '--force-with-lease' instead, and never on main/master."
        )

    if has_force_with_lease and targets_main:
        block(
            "Blocked: 'git push --force-with-lease' targeting main/master "
            "is not allowed."
        )

    if targets_main and not (has_force or has_force_with_lease):
        block("Blocked: 'git push' targeting main/master is not allowed.")


def check_git_commit(tokens: list[str]) -> None:
    if not is_git_subcommand(tokens, "commit"):
        return

    if any(t in ("--no-verify", "-n") for t in tokens[2:]):
        block("Blocked: 'git commit --no-verify'/'-n' is not allowed.")

    branch = current_branch()
    if branch in ("main", "master"):
        block(
            f"Blocked: 'git commit' while on branch '{branch}'. "
            "Create a feature branch first (see the git-branch-pr skill)."
        )


def check_git_dangerous(tokens: list[str], segment: str) -> None:
    if not tokens or tokens[0] != "git":
        return

    sub = tokens[1] if len(tokens) > 1 else ""

    if sub == "reset" and "--hard" in tokens[2:]:
        block("Blocked: 'git reset --hard' is not allowed.")

    if sub == "clean":
        flag_blob = "".join(t.lstrip("-") for t in tokens[2:] if t.startswith("-"))
        if "f" in flag_blob and ("d" in flag_blob or "x" in flag_blob):
            block("Blocked: 'git clean' with force+destructive flags is not allowed.")

    if sub == "rebase":
        branch = current_branch()
        if branch in ("main", "master"):
            block("Blocked: 'git rebase' while on main/master is not allowed.")

    if sub == "filter-branch":
        block("Blocked: 'git filter-branch' is not allowed.")

    if sub == "push" and "--mirror" in tokens[2:]:
        block("Blocked: 'git push --mirror' is not allowed.")

    if sub == "update-ref" and "-d" in tokens[2:]:
        block("Blocked: 'git update-ref -d' is not allowed.")

    if sub == "reflog" and len(tokens) > 2 and tokens[2] == "delete":
        block("Blocked: 'git reflog delete' is not allowed.")


def check_git_add(tokens: list[str]) -> None:
    if not tokens or tokens[0] != "git":
        return
    if len(tokens) < 2 or tokens[1] not in ("add", "stage"):
        return

    for raw in tokens[2:]:
        if raw.startswith("-"):
            continue
        normalized = raw.strip("'\"")
        norm_slash = normalized.replace("\\", "/")
        if (
            norm_slash in EXACT_PROTECTED_STAGE_FILES
            or normalized in EXACT_PROTECTED_STAGE_FILES
            or norm_slash.endswith((".coverage", "coverage.xml"))
        ):
            block(f"Blocked: staging protected file '{normalized}' is not allowed.")
        for pattern in PROTECTED_STAGE_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                block(
                    f"Blocked: staging path '{normalized}' under a protected "
                    "directory (data/, logs/, .venv/, venv/, htmlcov/) is not "
                    "allowed."
                )


def check_bash(command: str) -> None:
    for segment in split_commands(command):
        tokens = tokens_of(segment)
        check_git_push(tokens, segment)
        check_git_commit(tokens)
        check_git_dangerous(tokens, segment)
        check_git_add(tokens)


def check_edit_write(file_path: str) -> None:
    if not file_path:
        return
    normalized = file_path.replace("\\", "/")
    for pattern in PROTECTED_DIR_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            block(
                f"Blocked: writing to '{file_path}' under a protected data "
                "directory (data/, logs/, D:/L0_raw, D:/L1_processed) is not "
                "allowed."
            )
        if re.search(pattern, file_path, re.IGNORECASE):
            block(
                f"Blocked: writing to '{file_path}' under a protected data "
                "directory (data/, logs/, D:/L0_raw, D:/L1_processed) is not "
                "allowed."
            )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # If we can't parse the payload, fail open (allow) rather than
        # blocking unrelated tool calls due to a hook plumbing issue.
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    if tool_name == "Bash":
        command = tool_input.get("command", "") or ""
        check_bash(command)
    elif tool_name in ("Edit", "Write"):
        file_path = tool_input.get("file_path", "") or ""
        check_edit_write(file_path)

    sys.exit(0)


if __name__ == "__main__":
    main()
