---
name: release
description: Use when cutting a new release of eddypro-batch-processor — bumping the version, moving CHANGELOG [Unreleased] entries into a dated section, verifying the installed version, and tagging. Do not use for routine feature commits.
---

# release

## 1. Bump the version

- Edit `version = "..."` in `pyproject.toml` to the new version.
- **Do not** hand-edit `__version__` in
  `src/eddypro_batch_processor/__init__.py` — it is now derived
  automatically via `importlib.metadata` from the installed package
  metadata, so it must not be set manually.

## 2. Update CHANGELOG.md

- Move the contents of the `## [Unreleased]` section into a new dated
  section following [Keep a Changelog](https://keepachangelog.com/)
  format:

  ```markdown
  ## [Unreleased]

  ## [0.4.0] - 2026-08-18

  ### Added
  - ...

  ### Fixed
  - ...
  ```

- Leave `## [Unreleased]` at the top, empty, ready for the next cycle.
- Keep category headers (`Added`, `Changed`, `Deprecated`, `Removed`,
  `Fixed`, `Security`) consistent with existing entries.

## 3. Verify

Reinstall/refresh the editable install if needed, then confirm the
version resolves correctly:

```powershell
.venv\Scripts\Activate.ps1
pip install -e . --no-deps
python -c "import eddypro_batch_processor as m; print(m.__version__)"
```

The printed version must match the new `pyproject.toml` version.

## 4. Tag and push

```powershell
git tag v0.4.0
git push origin v0.4.0
```

Only push the tag once the version bump and CHANGELOG commit are merged to
`main` via the normal PR flow (see the `git-branch-pr` skill) — do not tag
an unmerged branch.
