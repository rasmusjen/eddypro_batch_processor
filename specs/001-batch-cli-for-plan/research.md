# Research Findings

## Decisions

- CLI framework: Typer for subcommands and friendly help UX.
- Profiling: psutil sampler at 1–2s; adaptive to keep overhead ≤5%.
- Checksums: Default blake3 (fast), optional sha256; record algorithm in provenance.
- HTML report: Jinja2 + Plotly, single-file offline via inline JS.
- Scenario execution: Sequential in initial release.

## Rationale

- Typer keeps CLI typed and discoverable; good help output.
- psutil balances observability with low overhead; sampling not tracing.
- blake3 outperforms sha256; offering sha256 covers compliance needs.
- Single-file HTML simplifies distribution and offline review.
- Sequential scenarios avoid I/O contention and ease profiling accuracy.

## Alternatives Considered

- Click/Argparse instead of Typer → similar capability, lower ergonomics.
- cProfile/py-spy for profiling → higher fidelity but more overhead and complexity.
- Multiple HTML assets → complicates offline usage.

## Open Items from Spec

- FR-A02: Clarify full QC preset taxonomy.
- FR-A03: Decide whether to include `--force` in initial scope.
- FR-A05: Define matrix size guardrails or confirmation.
