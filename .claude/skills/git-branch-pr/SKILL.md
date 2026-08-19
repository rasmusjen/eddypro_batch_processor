---
name: git-branch-pr
description: Use when creating a feature/fix branch, keeping a branch current with main, or opening/merging a pull request in this repo. Covers branch naming, never committing to main, rebase vs merge, gh pr create using the repo's PR template, CI-green requirement, squash-merge default, and safe force-push rules.
---

# git-branch-pr

## Branch naming and creation

- Prefixes: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, `refactor/<slug>`.
- Never commit directly to `main`.
- Always branch from an up-to-date `main`:
  ```powershell
  git checkout main
  git pull origin main
  git checkout -b feat/my-slug
  ```

## Keeping a branch current with main

- **Unpushed / solo work on the branch**: prefer `git rebase main` to keep
  history linear.
- **Once the branch is pushed and/or shared with others**: prefer
  `git merge main` instead of rebasing, to avoid rewriting shared history.

## Opening a PR

Use `gh pr create`, filling in the sections from
`.github/pull_request_template.md` (Summary, Problem, Approach, Changes
Made, Tests, Risks, Rollback Plan, Checklist):

```powershell
gh pr create --title "feat: short description" --body "$(cat <<'EOF'
## Summary
...

## Problem
...

## Approach
...

### Changes Made
- ...

## Tests
- ...

## Risks
- ...

## Rollback Plan
- ...

## Checklist
- [ ] Lint/format/typecheck clean (ruff, black, mypy)
- [ ] Tests updated; coverage >=70%
- [ ] Documentation updated (README, CHANGELOG, docs/)
- [ ] Pre-commit hooks pass
- [ ] CI pipeline green
EOF
)"
```

## Merging

- Require CI green before merge — do not merge on red or pending checks.
- Squash-merge is the default merge strategy for this repo.
- Delete the branch after merge (`gh pr merge --squash --delete-branch`, or
  delete manually if merged via the web UI).

## Force-pushing

- Never force-push shared/pushed branches with plain `--force`.
- If a force-push is genuinely needed after a rebase, use
  `--force-with-lease` only, and only on your own feature branch — never on
  `main`/`master`.
