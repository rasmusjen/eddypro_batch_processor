# Multi-Year Runs

This page walks through processing several years of data for one site with
the **same** processing settings. It is deliberately separate from
[SCENARIOS.md](SCENARIOS.md).

> A **multi-year run** applies the *same* processing settings across several
> years. A **scenario run** applies *several combinations of EddyPro
> processing parameters* (`rot_meth`, `tlag_meth`, `detrend_meth`,
> `despike_meth`, `hf_meth`) to the same year(s). They are independent
> features; this page covers the former.

If you want to compare parameter combinations, see [SCENARIOS.md](SCENARIOS.md)
instead. The two can be combined (a scenario matrix run also accepts multiple
`--years`), but this page focuses on the plain `run` command.

## Worked example: GL-Dsk, 2020-2025

The example below processes six years (2020-2025) of site `GL-Dsk` with
identical settings, parallelized across years with performance monitoring
enabled.

### Option 1: As a config file

[`examples/multi_year_config.yaml`](../examples/multi_year_config.yaml) is a
complete, ready-to-edit config for this scenario:

```yaml
eddypro_executable: "C:/Program Files/LI-COR/EddyPro-7.0.9/bin/eddypro_rp.exe"
site_id: GL-Dsk
years_to_process: [2020, 2021, 2022, 2023, 2024, 2025]
input_dir_pattern:  "D:/L0_raw/{site_id}/{year}/ec/rflux_csv"
output_dir_pattern: "D:/L1_processed/{site_id}/{year}/ec_rflux_sc26"
ecmd_file: "D:/L1_processed/{site_id}/ecmd/{site_id}_ecmd.csv"
multiprocessing: true
max_processes: 6
monitoring_enabled: true
metrics_interval_seconds: 1.0
reports_dir: "D:/L1_processed/GL-Dsk/reports/2020-2025"
report_charts: plotly
```

(See the file itself for the remaining required keys — `stream_output`,
`log_level`, and the optional `log_*` keys — needed for `validate` to pass.)

Run it:

```powershell
eddypro-batch --config examples/multi_year_config.yaml validate
eddypro-batch --config examples/multi_year_config.yaml run --dry-run
eddypro-batch --config examples/multi_year_config.yaml run
```

### Option 2: As pure CLI (no config file edits)

Every setting can be supplied on the command line instead, overriding
whatever is in `config/config.yaml`:

```powershell
eddypro-batch run `
  --site GL-Dsk `
  --years 2020 2021 2022 2023 2024 2025 `
  --input-dir-pattern  "D:/L0_raw/{site_id}/{year}/ec/rflux_csv" `
  --output-dir-pattern "D:/L1_processed/{site_id}/{year}/ec_rflux_sc26" `
  --rot-meth 1 --tlag-meth 2 --detrend-meth 0 --despike-meth 0 --hf-meth 1 `
  --mp --max-proc 6 `
  --metrics-interval 1.0 `
  --reports-dir "D:/L1_processed/GL-Dsk/reports/2020-2025" `
  --report-charts plotly
```

Note that `--rot-meth`, `--tlag-meth`, `--detrend-meth`, `--despike-meth`, and
`--hf-meth` on `run` each take a single value — they patch the same INI
parameter for every year, which is exactly the "same settings, many years"
behavior a multi-year run is for. (On `scenarios`, the same flag names accept
*multiple* values and form a Cartesian product instead — see
[SCENARIOS.md](SCENARIOS.md).)

## Always dry-run first

Rehearse before committing to a multi-hour run:

```powershell
eddypro-batch --config examples/multi_year_config.yaml run --dry-run
```

`--dry-run`:
- Creates each year's output directory and `.eddypro` project file
- Materializes `.metadata` and `_dynamic_metadata.txt` from the ECMD file
- Runs the same preflight validation as a real run (input path exists, files
  present, metadata sane)
- Writes the run manifest and HTML report as if all years "succeeded"

`--dry-run` does **not**:
- Invoke `eddypro_rp` or `eddypro_fcc`
- Produce any EddyPro output CSVs
- Sample performance metrics (there is no process to monitor)

## Monitoring overhead: `--no-monitor`

Performance monitoring samples the whole EddyPro process tree (CPU, memory,
disk reads/writes) at `metrics_interval_seconds`. It has real but usually
small overhead. For maximum throughput on a large batch — many years, tight
disk budget, or a machine you also need for other work — disable it:

```powershell
eddypro-batch --config examples/multi_year_config.yaml run --no-monitor
```

or set `monitoring_enabled: false` in the config. With monitoring disabled,
no `metrics_*.csv` files are written and `metrics_interval_seconds` is
ignored. Keep monitoring on while you are still tuning `max_processes` — the
bottleneck report is what tells you whether to raise or lower it.

## What lands where

For each processed year:

```
{output_dir_pattern}/{site_id}/{year}/          # e.g. .../GL-Dsk/2021/ec_rflux_sc26/
├── GL-Dsk.eddypro                                # generated project file
├── GL-Dsk.metadata
├── GL-Dsk_dynamic_metadata.txt
├── eddypro_GL-Dsk_fluxnet_*.csv
├── eddypro_GL-Dsk_full_output_*.csv
├── eddypro_GL-Dsk_metadata_*.csv
├── eddypro_GL-Dsk_qc_details_*.csv
├── metrics_rp.csv                                # performance samples, eddypro_rp phase
└── metrics_fcc.csv                                # performance samples, eddypro_fcc phase
```

And once, for the whole run, under `reports_dir`:

```
D:/L1_processed/GL-Dsk/reports/2020-2025/
├── run_manifest.json
└── run_report.html
```

`run_manifest.json` includes a `years[]` array with one entry per year —
`{year, status, duration_seconds, error, output_dir}` — so a failed year is
visible in the manifest even though the run as a whole continues. It also
carries a `provenance` block (git SHA + dirty flag, package version, EddyPro
executable path/checksum, `sys.argv`), a real SHA256 `config_checksum`, and
`manifest_schema_version: 2`. See [REPORTING.md](REPORTING.md) for the full
schema.

## Reading the bottleneck traffic light

`run_report.html` classifies each year's run as CPU, MEMORY,
DISK_THROUGHPUT, or DISK_IOPS bound, based on the sampled metrics. Use it to
decide whether `max_processes` is set well:

| Classification | What it means | What to do |
|---|---|---|
| CPU | The **machine** is compute-bound; cores are the limit | Lower `max_processes` toward the physical core count if you see thrashing; otherwise this is healthy utilization |
| CPU_SINGLE_CORE | EddyPro is pegging one core while the machine sits idle. This is the normal state for a single-year run, because `eddypro_rp` is largely single-threaded | Raise `max_processes` and run more years concurrently. A faster disk will not help |
| MEMORY | Workers are approaching available RAM | Lower `max_processes`, or process fewer years concurrently |
| DISK_THROUGHPUT | Aggregate read/write MB/s is saturating the disk | Lower `max_processes`, or move input/output to faster storage (SSD/NVMe) |
| DISK_IOPS | Many small reads/writes are the limit (common with many small raw files) | Move data to faster storage; concatenating raw files can help more than adding workers |

The metrics CSV carries three different CPU columns and they answer different
questions:

| Column | Meaning | Use it for |
|---|---|---|
| `cpu_percent_of_core` | 100 = one core fully busy, 200 = two | Is the workload itself pinned by single-thread speed? |
| `system_cpu_percent` | Machine-wide utilisation | Is the *machine* full? This drives the CPU verdict |
| `cpu_percent` | The process tree's share of the whole machine | Comparing one worker's footprint against the box |

`cpu_percent` is divided by the logical core count, so on a 20-thread machine a
single-threaded EddyPro saturating one core reads as ~5%. That is not idleness --
check `cpu_percent_of_core` before concluding a run was cheap.

## Hybrid CPUs: pin EddyPro to the performance cores

On Intel hybrid CPUs (12th generation and later) the cores are not all equal:
an i7-12700K has 8 performance cores (logical 0-15) and 4 efficiency cores
(16-19). Windows will park a long-running background process on the efficiency
cores, especially while you are using the machine for something else.

`eddypro_rp` is single-threaded, so this costs about a factor of two. Measured
on a 12700K, one year of 10 Hz data:

| | Wall time | s per flux period | `cpu_percent_of_core` p95 |
|---|---|---|---|
| Pinned to P-cores | 241 s, 241 s | 0.70 | 102.6% |
| Unpinned | 474 s, 501 s | 1.39, 1.47 | 96.5-97.8% |

Note the last column: **CPU utilisation is identical**. A demoted run looks
perfectly healthy in the bottleneck report -- it is saturating a core, it is
just a slower core. Only the `work_items_per_s` throughput series reveals it.
System CPU sat at 17-21% in all four runs, so this is core placement, not
contention.

Pinning also makes runs reproducible: the two pinned runs agreed exactly, while
the unpinned pair differed by 5.7%.

Set `cpu_affinity` in the config and the pipeline handles it -- child
processes inherit affinity, so pinning the launching process covers the workers
and the EddyPro executables they run:

```yaml
cpu_affinity: performance    # or an explicit list, e.g. [0, 1, 2, ..., 15]
```

Auto-detection derives the split from the core counts and logs what it chose.
On a CPU without efficiency cores there is nothing to gain and affinity is left
alone. See [CONFIG.md](CONFIG.md#cpu_affinity) for the details.

Check your own topology with:

```powershell
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
```

## Choosing `max_processes`

Start from **one worker per year** and cap it by whichever is smaller:

- Physical CPU cores available (leave 1-2 free for the OS and monitoring)
- What your input/output disks can sustain without becoming the bottleneck
  (see the traffic-light table above)

For the GL-Dsk example (6 years, `max_processes: 6`), if the bottleneck
report comes back DISK_THROUGHPUT or DISK_IOPS, drop `max_processes` to 3-4
before adding more years, or move `D:/L0_raw` / `D:/L1_processed` to faster
storage.

## Caveats

- **Years are processed independently.** A failure in one year (bad ECMD
  row, missing input files, EddyPro crash) is logged and does not stop the
  other years — the run continues and the failure is recorded per-year in
  the manifest's `years[]` array.
- **`reports_dir` defaults to the first year's output directory** if you
  don't set it (see `cli.py` around line 533). For a multi-year run this
  default is confusing (why would the 2025 report live under `.../2020/`?),
  which is why the example above sets `reports_dir` explicitly.
- Both `run` and `scenarios` execute `eddypro_rp` followed by `eddypro_fcc`
  for every year; if `eddypro_rp` fails, `eddypro_fcc` is skipped for that
  year and the year is marked failed.

## See also

- [SCENARIOS.md](SCENARIOS.md) – parameter-combination testing (the other
  kind of "multi" run)
- [CONFIG.md](CONFIG.md) – full configuration key reference
- [REPORTING.md](REPORTING.md) – manifest and report schema, provenance
- [USAGE.md](USAGE.md) – complete CLI reference
