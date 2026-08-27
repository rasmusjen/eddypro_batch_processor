#!/usr/bin/env python3
"""PostToolUse hook: auto-format and lint a Python file after Edit/Write.

Reads a JSON hook payload on stdin with `tool_name` and `tool_input`.
Runs `black` then `ruff check --fix` on the touched file. If ruff still
reports issues afterwards, prints them to stderr and exits 2 so the model
sees them as advisory feedback (not a hard block).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def project_python() -> str:
    """Interpreter that actually has black and ruff installed.

    The hook itself may be run by any interpreter -- typically the system
    Python, which has no dev tooling. Prefer the project virtualenv so the
    formatters are found; fall back to whatever is running us.
    """
    root = Path(__file__).resolve().parents[2]
    for candidate in (
        root / ".venv" / "Scripts" / "python.exe",  # Windows
        root / ".venv" / "bin" / "python",  # POSIX
    ):
        if candidate.exists():
            return str(candidate)
    return sys.executable


def missing_module(result: subprocess.CompletedProcess) -> bool:
    """True when the interpreter ran but the tool is not installed.

    `python -m ruff` with ruff absent exits non-zero with a normal message
    rather than raising, so this case is indistinguishable from a lint failure
    unless the output is inspected.
    """
    return "No module named" in ((result.stderr or "") + (result.stdout or ""))


def run(args: list[str]) -> subprocess.CompletedProcess | None:
    try:
        # nosec B603 - args are built here from sys.executable plus a fixed
        # tool name; no shell is involved and nothing is user-supplied.
        return subprocess.run(  # noqa: S603  # nosec B603
            args, check=False, capture_output=True, text=True, timeout=60
        )
    except FileNotFoundError:
        return None
    except Exception:
        return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "") or ""

    if not file_path.endswith(".py"):
        sys.exit(0)

    if not os.path.exists(file_path):
        sys.exit(0)

    python = project_python()

    black_result = run([python, "-m", "black", file_path])
    if black_result is None or missing_module(black_result):
        # black not installed / not runnable - tolerate silently.
        sys.exit(0)

    ruff_fix_result = run([python, "-m", "ruff", "check", "--fix", file_path])
    if ruff_fix_result is None or missing_module(ruff_fix_result):
        # ruff not installed / not runnable - tolerate silently.
        sys.exit(0)

    ruff_check_result = run([python, "-m", "ruff", "check", file_path])
    if ruff_check_result is None or missing_module(ruff_check_result):
        sys.exit(0)

    if ruff_check_result.returncode != 0:
        output = (ruff_check_result.stdout or "") + (ruff_check_result.stderr or "")
        print(output.strip(), file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
