---
name: git-commit
description: Use when the user asks to commit changes in this repo. Covers deliberate file staging (never bulk `git add -A`/`.`), Conventional Commits message style matching this repo's history, running pre-commit on staged files, and files that must never be staged (config/config.yaml, data/, logs/, venv dirs, coverage artifacts).
---

# git-commit

## Staging: deliberate, never bulk

- Never run `git add -A` or `git add .`.
- Enumerate each path explicitly, e.g. `git add src/eddypro_batch_processor/core.py tests/test_core.py`.
- Before staging, run `git status` to see the full set of changes and decide,
  file by file, what belongs in this commit.
- Never stage:
  - `config/config.yaml` (the user's live machine-specific working config)
  - anything under `data/`, `logs/`, `.venv/`, `venv/`, `htmlcov/`
  - `.coverage`, `coverage.xml`
  If any of these show up in `git status` as modified/untracked, leave them
  unstaged and mention it to the user rather than silently including them.

## Commit message style

Follow Conventional Commits, matching this repo's actual history:

```
feat: add metadata population planning and analysis docs
fix(cli): correct exit code on validation failure
docs: align logging config docs
refactor: simplify project filenames and clean up docs
test: add tests for ECMD validation
chore: bump dependency pins
```

- Type prefixes: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
- Optional scope in parens, e.g. `feat(logging):`, `fix(core):`.
- Subject in imperative mood, no trailing period.
- Add a body with bullet points for anything non-trivial.

## Before committing

1. `git status` — confirm exactly the intended files are staged and nothing
   from the never-stage list slipped in.
2. `git diff --staged` — review the actual diff, not just filenames.
3. `pre-commit run --files <staged files>` — run hooks against just the
   staged files before committing (list them explicitly, don't use
   `--all-files` for a routine commit).
4. Fix anything pre-commit flags, re-stage, and re-run before committing.

## Never

- Never use `git commit --no-verify` or `-n` to skip hooks.
- Never commit on `main`/`master` directly — see the `git-branch-pr` skill.
