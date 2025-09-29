"""Provenance capture utilities.

This module captures an immutable JSON manifest describing a processing run.
It intentionally avoids heavy dependencies; only stdlib is used.

Manifest fields (top-level):
  schema_version: int (bump if structure changes)
  created_at: ISO8601 UTC timestamp
  duration_seconds: float (if end timestamp provided)
  git: { commit, branch, dirty }
  python: { version }
  environment: { packages: {name: version} } (optional subset)
  config: { hash, redacted_keys: [...], excerpt: {...subset...} }
  run: { site_id, years, total_raw_files, processed_raw_files, input_root, processed_root }

Atomic write: write to tmp file then replace to avoid partial reads.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Iterable

SCHEMA_VERSION = 1


@dataclass
class RunContext:
    site_id: str
    years: Iterable[int]
    total_raw_files: int
    processed_raw_files: int
    input_root: Path
    processed_root: Path
    config: Dict[str, Any]
    redact_keys: Iterable[str] | None = None
    include_environment: bool = True
    start_time: float | None = None
    end_time: float | None = None


def _sha256_json(data: Any) -> str:
    blob = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _git_info() -> Dict[str, Any]:
    def _run(cmd: list[str]) -> str:
        try:
            return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return ""

    commit = _run(["git", "rev-parse", "HEAD"])
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    status = _run(["git", "status", "--porcelain"])
    dirty = bool(status)
    return {"commit": commit, "branch": branch, "dirty": dirty}


def _environment_packages() -> Dict[str, str]:
    # Lightweight fallback: try pip freeze; ignore errors.
    try:
        out = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], stderr=subprocess.DEVNULL).decode()
        pkgs: Dict[str, str] = {}
        for line in out.splitlines():
            if "==" in line:
                name, ver = line.split("==", 1)
                pkgs[name.lower()] = ver
        return pkgs
    except Exception:
        return {}


def _redact(config: Dict[str, Any], redact_keys: Iterable[str] | None) -> Dict[str, Any]:
    if not redact_keys:
        return config
    lowered = {k.lower() for k in redact_keys}

    def _walk(obj: Any):
        if isinstance(obj, dict):
            return {k: ("***REDACTED***" if k.lower() in lowered else _walk(v)) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(v) for v in obj]
        return obj

    return _walk(config)  # type: ignore[return-value]


def generate_provenance(run_dir: Path, ctx: RunContext) -> Path:
    """Generate and write a provenance manifest in ``run_dir``.

    Returns path to the written manifest file.
    """
    run_dir.mkdir(parents=True, exist_ok=True)

    start = ctx.start_time or time.time()
    end = ctx.end_time or time.time()

    redacted_config = _redact(ctx.config, ctx.redact_keys)
    config_hash = _sha256_json(redacted_config)

    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(end)),
        "duration_seconds": round(end - start, 3),
        "git": _git_info(),
        "python": {"version": sys.version.split()[0]},
        "config": {
            "hash": config_hash,
            "redacted_keys": list(ctx.redact_keys or []),
            "excerpt": redacted_config,
        },
        "run": {
            "site_id": ctx.site_id,
            "years": list(ctx.years),
            "total_raw_files": ctx.total_raw_files,
            "processed_raw_files": ctx.processed_raw_files,
            "input_root": str(ctx.input_root),
            "processed_root": str(ctx.processed_root),
        },
    }

    if ctx.include_environment:
        manifest["environment"] = {"packages": _environment_packages()}

    # Atomic write
    target = run_dir / "provenance.json"
    tmp = target.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, target)
    return target

__all__ = ["RunContext", "generate_provenance"]
