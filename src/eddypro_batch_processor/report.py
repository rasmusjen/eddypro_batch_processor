"""
EddyPro Batch Processor Reporting Module.

Generates run manifests (JSON) and HTML reports with performance metrics,
scenario summaries, and provenance information.
"""

import csv
import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
import yaml

logger = logging.getLogger(__name__)

# Optional dependencies with fallbacks
PLOTLY_AVAILABLE = False
go: Any = None
make_subplots: Any = None

try:
    import plotly  # noqa: F401
    import plotly.graph_objects as go  # type: ignore[no-redef]
    from plotly.subplots import make_subplots  # type: ignore[no-redef]

    PLOTLY_AVAILABLE = True
except ImportError:
    logger.debug("Plotly not available; charts will fall back to SVG or none")


#: Bumped when the run manifest structure changes in a way consumers must notice.
MANIFEST_SCHEMA_VERSION = 2


def compute_config_checksum(config: dict[str, Any]) -> str:
    """
    Compute a stable SHA256 checksum of a configuration mapping.

    Replaces the previous ``str(hash(json.dumps(...)))``, which used Python's
    built-in ``hash()``. That is salted per-process by ``PYTHONHASHSEED``, so the
    same configuration produced a different checksum on every run, making the
    field useless for comparing runs.
    """
    canonical = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_git_provenance(repo_root: Path | None = None) -> dict[str, Any]:
    """
    Capture the git commit the code was run from.

    Degrades gracefully: outside a git repository, or without git installed, the
    fields are simply reported as unavailable rather than raising.
    """
    cwd = repo_root or Path(__file__).resolve().parent
    info: dict[str, Any] = {"git_sha": None, "git_dirty": None, "git_branch": None}
    try:
        info["git_sha"] = subprocess.check_output(  # nosec B603 B607
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        info["git_branch"] = subprocess.check_output(  # nosec B603 B607
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        status = subprocess.check_output(  # nosec B603 B607
            ["git", "status", "--porcelain"],
            cwd=cwd,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        info["git_dirty"] = bool(status.strip())
    except Exception:
        logger.debug("Git provenance unavailable")
    return info


def get_provenance(config: dict[str, Any]) -> dict[str, Any]:
    """
    Assemble the reproducibility block recorded in the run manifest.

    Captures the tool version, git state, the invoking command line, and the
    EddyPro executable actually used (path plus checksum, so a silent upgrade of
    the binary is detectable after the fact).
    """
    # Imported lazily: the package __init__ imports core, which imports this
    # module, so a top-level import here would be circular.
    from . import __version__  # noqa: PLC0415

    provenance: dict[str, Any] = {
        "tool_version": __version__,
        "command_line": list(sys.argv),
        **get_git_provenance(),
    }

    exe = config.get("eddypro_executable")
    eddypro: dict[str, Any] = {"path": str(exe) if exe else None, "checksum": None}
    if exe:
        try:
            exe_path = Path(exe)
            if exe_path.exists():
                eddypro["checksum"] = compute_file_checksum(exe_path)
                # EddyPro embeds its version in the install directory name,
                # e.g. .../EddyPro-7.0.9/bin/eddypro_rp.exe
                for part in exe_path.parts:
                    if part.lower().startswith("eddypro-"):
                        eddypro["version"] = part.split("-", 1)[1]
                        break
        except Exception:
            logger.debug("Could not checksum EddyPro executable")
    provenance["eddypro"] = eddypro

    return provenance


def compute_file_checksum(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Compute checksum of a file.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hexadecimal checksum string

    Raises:
        FileNotFoundError: If file does not exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    hash_obj = hashlib.new(algorithm)
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def get_python_environment_info() -> dict[str, Any]:
    """
    Capture Python environment information.

    Returns:
        Dictionary with Python version, platform, and key package versions
    """
    env_info: dict[str, Any] = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "processor": platform.processor(),
    }

    # Capture versions of key packages
    package_versions: dict[str, str] = {}
    try:
        package_versions["PyYAML"] = getattr(yaml, "__version__", "unknown")
    except AttributeError:
        package_versions["PyYAML"] = "unknown"

    try:
        package_versions["psutil"] = getattr(psutil, "__version__", "unknown")
    except AttributeError:
        package_versions["psutil"] = "not installed"

    if PLOTLY_AVAILABLE:
        try:
            import plotly as plotly_mod  # noqa: PLC0415

            package_versions["plotly"] = plotly_mod.__version__
        except (ImportError, AttributeError):
            package_versions["plotly"] = "unknown"
    else:
        package_versions["plotly"] = "not installed"

    env_info["package_versions"] = package_versions

    return env_info


def generate_scenario_manifest(
    scenario_name: str,
    scenario_params: dict[str, Any],
    project_file: Path,
    output_dir: Path,
    start_time: datetime,
    end_time: datetime,
    success: bool,
    metrics_summary: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """
    Generate a manifest for a single scenario run.

    Args:
        scenario_name: Name/identifier of the scenario
        scenario_params: Dictionary of scenario parameters (e.g., rotation method)
        project_file: Path to the EddyPro project file used
        output_dir: Path to the output directory
        start_time: Scenario start timestamp
        end_time: Scenario end timestamp
        success: Whether the scenario completed successfully
        metrics_summary: Optional performance metrics summary
        error_message: Optional error message if failed

    Returns:
        Dictionary containing scenario manifest data
    """
    duration_seconds = (end_time - start_time).total_seconds()

    manifest = {
        "scenario_name": scenario_name,
        "scenario_params": scenario_params,
        "project_file": str(project_file),
        "output_dir": str(output_dir),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration_seconds,
        "success": success,
    }

    if metrics_summary:
        manifest["metrics_summary"] = metrics_summary

    if error_message:
        manifest["error_message"] = error_message

    return manifest


def write_scenario_manifest(manifest: dict[str, Any], output_path: Path) -> None:
    """
    Write scenario manifest to JSON file.

    Args:
        manifest: Scenario manifest dictionary
        output_path: Path to write manifest JSON
    """
    try:
        with output_path.open("w") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Scenario manifest written to {output_path}")
    except Exception:
        logger.exception(f"Failed to write scenario manifest to {output_path}")


def collect_eddypro_output_files(
    output_dir: Path, site_id: str
) -> dict[str, list[str]]:
    """
    Collect all EddyPro output CSV files matching standard patterns.

    Scans the specified output directory for EddyPro CSV outputs and returns
    absolute paths grouped by file type.

    Args:
        output_dir: Path to the EddyPro output directory
        site_id: Site identifier to match in filenames

    Returns:
        Dictionary mapping file type to sorted list of absolute path strings:
        - "fluxnet_files": eddypro_{site_ID}_fluxnet_*.csv
        - "full_output_files": eddypro_{site_ID}_full_output_*.csv
        - "metadata_files": eddypro_{site_ID}_metadata_*.csv
        - "qc_details_files": eddypro_{site_ID}_qc_details*.csv

    Example:
        >>> files = collect_eddypro_output_files(Path("/output"), "GL-ZaF")
        >>> files["fluxnet_files"]
        ['/output/eddypro_GL-ZaF_fluxnet_2024-11-18T185928_adv.csv']
    """
    patterns = {
        "fluxnet_files": f"eddypro_{site_id}_fluxnet_*.csv",
        "full_output_files": f"eddypro_{site_id}_full_output_*.csv",
        "metadata_files": f"eddypro_{site_id}_metadata_*.csv",
        "qc_details_files": f"eddypro_{site_id}_qc_details*.csv",
    }

    collected: dict[str, list[str]] = {}

    for file_type, pattern in patterns.items():
        matching_files = sorted(output_dir.glob(pattern))
        # Convert to absolute path strings
        collected[file_type] = [str(f.resolve()) for f in matching_files]
        logger.debug(f"Found {len(collected[file_type])} {file_type} in {output_dir}")

    return collected


def generate_run_manifest(
    run_id: str,
    config: dict[str, Any],
    config_checksum: str,
    site_id: str,
    years_processed: list[int],
    scenarios: list[dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
    overall_success: bool,
    output_dirs: list[Path],
    provenance: dict[str, Any] | None = None,
    years: list[dict[str, Any]] | None = None,
    errors: list[str] | None = None,
    status: str = "completed",
    metrics_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a run-level manifest capturing all scenarios and metadata.

    Args:
        run_id: Unique identifier for this run
        config: Configuration dictionary used for the run
        config_checksum: Stable SHA256 checksum of the config
        site_id: Site identifier
        years_processed: Years that completed successfully (derived, kept for
            backwards compatibility -- prefer ``years`` for full detail)
        scenarios: List of scenario manifests
        start_time: Run start timestamp
        end_time: Run end timestamp
        overall_success: Whether all scenarios succeeded
        output_dirs: List of output directories created
        provenance: Provenance information (git SHA, tool version, EddyPro build)
        years: Per-year records ``{year, status, duration_seconds, error,
            output_dir}``. A failed year appears here even though it is absent
            from ``years_processed``.
        errors: Run-level error messages
        status: ``"running"`` for the manifest written at run start, then
            ``"completed"`` or ``"failed"``
        metrics_summary: Bottleneck analysis and performance summary

    Returns:
        Dictionary containing run manifest data
    """
    duration_seconds = (end_time - start_time).total_seconds()

    # Collect EddyPro output files from all output directories
    output_files: dict[str, dict[str, list[str]]] = {}
    for output_dir in output_dirs:
        if output_dir.exists():
            collected = collect_eddypro_output_files(output_dir, site_id)
            output_files[str(output_dir)] = collected

    manifest = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "status": status,
        "timestamp": start_time.isoformat(),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration_seconds,
        "site_id": site_id,
        "years_processed": years_processed,
        "years": years if years is not None else [],
        "config_checksum": config_checksum,
        "config_snapshot": config,  # Include full config for reproducibility
        "overall_success": overall_success,
        "scenarios": scenarios,
        "errors": errors if errors is not None else [],
        "output_dirs": [str(d) for d in output_dirs],
        "output_files": output_files,  # Detailed file inventory
        "environment": get_python_environment_info(),
        "dry_run": config.get("dry_run", False),  # Track if this was a dry run
    }

    if provenance:
        manifest["provenance"] = provenance
    if metrics_summary:
        manifest["metrics_summary"] = metrics_summary

    return manifest


def write_run_manifest(manifest: dict[str, Any], output_path: Path) -> bool:
    """
    Write the run manifest to JSON atomically.

    The manifest is serialised to a temporary file in the destination directory
    and then moved into place with :func:`os.replace`. Writing directly to the
    destination meant that a crash mid-write destroyed the previous good manifest
    and left invalid JSON behind.

    A copy is also archived under ``manifests/run_manifest_{run_id}.json`` so that
    consecutive runs against the same output tree do not erase each other's
    provenance.

    Args:
        manifest: Run manifest dictionary
        output_path: Path to write manifest JSON

    Returns:
        True if the manifest was written successfully.
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = output_path.with_name(output_path.name + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, default=str)
        os.replace(tmp_path, output_path)
        logger.info(f"Run manifest written to {output_path}")
    except Exception:
        logger.exception(f"Failed to write run manifest to {output_path}")
        return False

    # Archive a per-run copy. Failure here is not fatal: the canonical manifest
    # is already safely in place.
    try:
        run_id = manifest.get("run_id")
        if run_id:
            archive_dir = output_path.parent / "manifests"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_path = archive_dir / f"run_manifest_{run_id}.json"
            with archive_path.open("w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, default=str)
    except Exception:
        logger.debug("Could not archive per-run manifest copy")

    return True


def load_metrics_from_csv(metrics_csv_path: Path) -> list[dict[str, Any]]:
    """
    Load performance metrics from CSV file.

    Args:
        metrics_csv_path: Path to metrics CSV file

    Returns:
        List of metric records as dictionaries
    """
    metrics = []
    try:
        with metrics_csv_path.open("r") as f:
            reader = csv.DictReader(f)
            numeric_fields = (
                "cpu_percent",
                "memory_mb",
                "read_mb",
                "write_mb",
                "read_mb_per_s",
                "write_mb_per_s",
                "read_iops",
                "write_iops",
                "relative_time",
                "system_cpu_percent",
                "system_memory_percent",
            )
            for row in reader:
                # Coerce per field rather than in one block: a single blank cell
                # must not abandon the remaining conversions for that row.
                for name in numeric_fields:
                    if name not in row:
                        continue
                    try:
                        row[name] = (
                            float(row[name]) if row[name] not in ("", None) else 0.0
                        )
                    except (TypeError, ValueError):
                        row[name] = 0.0
                metrics.append(row)
    except Exception:
        logger.warning(f"Failed to load metrics from {metrics_csv_path}")
    return metrics


def generate_plotly_charts(
    metrics: list[dict[str, Any]], scenario_name: str = "Run"
) -> str | None:
    """
    Generate interactive Plotly charts from metrics data.

    Args:
        metrics: List of metric records
        scenario_name: Name of the scenario for chart title

    Returns:
        HTML string containing the Plotly chart, or None if unavailable
    """
    if not PLOTLY_AVAILABLE or not metrics or go is None or make_subplots is None:
        return None

    try:
        # Extract time series
        timestamps = [m.get("timestamp", i) for i, m in enumerate(metrics)]
        cpu_percent = [m.get("cpu_percent", 0) for m in metrics]
        memory_mb = [m.get("memory_mb", 0) for m in metrics]
        read_mb = [m.get("read_mb", 0) for m in metrics]
        write_mb = [m.get("write_mb", 0) for m in metrics]

        # Create subplots
        fig = make_subplots(
            rows=3,
            cols=1,
            subplot_titles=(
                f"{scenario_name} - CPU Usage",
                f"{scenario_name} - Memory Usage",
                f"{scenario_name} - Disk I/O",
            ),
            vertical_spacing=0.1,
        )

        # CPU chart
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=cpu_percent,
                mode="lines",
                name="CPU %",
                line=dict(color="blue"),
            ),
            row=1,
            col=1,
        )

        # Memory chart
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=memory_mb,
                mode="lines",
                name="Memory (MB)",
                line=dict(color="green"),
            ),
            row=2,
            col=1,
        )

        # Disk I/O chart
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=read_mb,
                mode="lines",
                name="Read (MB)",
                line=dict(color="orange"),
            ),
            row=3,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=write_mb,
                mode="lines",
                name="Write (MB)",
                line=dict(color="red"),
            ),
            row=3,
            col=1,
        )

        # Update layout
        fig.update_xaxes(title_text="Sample", row=3, col=1)
        fig.update_yaxes(title_text="CPU %", row=1, col=1)
        fig.update_yaxes(title_text="Memory (MB)", row=2, col=1)
        fig.update_yaxes(title_text="Disk I/O (MB)", row=3, col=1)

        fig.update_layout(
            height=900,
            showlegend=True,
            title_text=f"Performance Metrics: {scenario_name}",
        )

    except Exception:
        logger.exception("Failed to generate Plotly charts")
        return None
    else:
        html_str: str = fig.to_html(full_html=False, include_plotlyjs="cdn")
        return html_str


def generate_html_report(
    run_manifest: dict[str, Any],
    scenario_metrics: dict[str, list[dict[str, Any]]] | None = None,
    chart_engine: str = "plotly",
    output_path: Path | None = None,
) -> str:
    """
    Generate an HTML report from run manifest and metrics.

    Args:
        run_manifest: Run manifest dictionary
        scenario_metrics: Optional dictionary mapping scenario names to metrics
        chart_engine: Chart engine to use ("plotly", "svg", or "none")
        output_path: Optional path to write the HTML report

    Returns:
        HTML string of the report
    """
    html_parts = []

    # HTML header
    html_parts.append(
        """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EddyPro Batch Processing Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: auto;
            background: white;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1, h2, h3 {
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        table, th, td {
            border: 1px solid #ddd;
        }
        th, td {
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .success {
            color: green;
            font-weight: bold;
        }
        .failure {
            color: red;
            font-weight: bold;
        }
        .summary-box {
            background-color: #e7f3ff;
            padding: 15px;
            border-left: 4px solid #2196F3;
            margin: 20px 0;
        }
        .chart-container {
            margin: 30px 0;
        }
    </style>
</head>
<body>
    <div class="container">
"""
    )

    # Report title and summary
    run_id = run_manifest.get("run_id", "unknown")
    timestamp = run_manifest.get("timestamp", "unknown")
    duration = run_manifest.get("duration_seconds", 0)
    site_id = run_manifest.get("site_id", "unknown")
    years = run_manifest.get("years_processed", [])
    overall_success = run_manifest.get("overall_success", False)
    status_class = "success" if overall_success else "failure"
    status_text = "SUCCESS" if overall_success else "FAILURE"

    html_parts.append(
        f"""
        <h1>EddyPro Batch Processing Report</h1>
        <div class="summary-box">
            <h2>Run Summary</h2>
            <p><strong>Run ID:</strong> {run_id}</p>
            <p><strong>Timestamp:</strong> {timestamp}</p>
            <p><strong>Duration:</strong> {duration:.2f} seconds ({duration / 60:.2f} minutes)</p>
            <p><strong>Site ID:</strong> {site_id}</p>
            <p><strong>Years Processed:</strong> {", ".join(map(str, years))}</p>
            <p><strong>Overall Status:</strong> <span class="{status_class}">{status_text}</span></p>
        </div>
"""
    )

    # Performance health check: traffic-light bottleneck summary. Placed directly
    # under the run summary because it is the first thing a user wants to know.
    metrics_summary = run_manifest.get("metrics_summary") or {}
    perf_entries = metrics_summary.get("scenarios", [])
    if perf_entries:
        colours = {
            "RED": "#e74c3c",
            "YELLOW": "#f39c12",
            "GREEN": "#27ae60",
            "UNKNOWN": "#95a5a6",
        }

        def _dot(status: str) -> str:
            colour = colours.get(status, colours["UNKNOWN"])
            return (
                f'<span style="display:inline-block;width:12px;height:12px;'
                f'border-radius:50%;background:{colour};margin-right:6px;"></span>'
                f"{status}"
            )

        html_parts.append(
            f"""
        <h2>Performance Health Check</h2>
        <p><strong>Primary bottleneck:</strong>
           {metrics_summary.get("primary_bottleneck", "UNKNOWN")}</p>
        <table>
            <tr>
                <th>Run</th><th>CPU</th><th>Memory</th><th>Disk</th>
                <th>Bottleneck</th><th>CPU p95</th><th>Peak RAM (MB)</th>
                <th>Read (MB)</th><th>Write (MB)</th>
            </tr>
"""
        )
        for entry in perf_entries:
            cpu = entry.get("cpu", {}) or {}
            html_parts.append(
                f"""            <tr>
                <td>{entry.get("scenario_name", "?")}</td>
                <td>{_dot(entry.get("cpu_status", "UNKNOWN"))}</td>
                <td>{_dot(entry.get("memory_status", "UNKNOWN"))}</td>
                <td>{_dot(entry.get("disk_status", "UNKNOWN"))}</td>
                <td><strong>{entry.get("primary_bottleneck", "?")}</strong></td>
                <td>{cpu.get("p95", 0):.1f}%</td>
                <td>{entry.get("peak_memory_mb", 0):.0f}</td>
                <td>{entry.get("total_read_mb", 0):.0f}</td>
                <td>{entry.get("total_write_mb", 0):.0f}</td>
            </tr>
"""
            )
        html_parts.append("        </table>\n")
        for entry in perf_entries:
            if entry.get("explanation"):
                html_parts.append(
                    f'        <p><em>{entry.get("scenario_name", "?")}:</em> '
                    f'{entry["explanation"]}</p>\n'
                )

    # Per-year results, including years that failed
    year_records = run_manifest.get("years", [])
    if year_records:
        html_parts.append(
            """
        <h2>Per-Year Results</h2>
        <table>
            <tr><th>Year</th><th>Status</th><th>Duration (s)</th><th>Error</th></tr>
"""
        )
        for rec in year_records:
            html_parts.append(
                f"            <tr><td>{rec.get('year', '?')}</td>"
                f"<td>{rec.get('status', '?')}</td>"
                f"<td>{rec.get('duration_seconds', 0):.1f}</td>"
                f"<td>{rec.get('error') or ''}</td></tr>\n"
            )
        html_parts.append("        </table>\n")

    # Scenario summary table
    scenarios = run_manifest.get("scenarios", [])
    if scenarios:
        html_parts.append(
            """
        <h2>Scenario Results</h2>
        <table>
            <tr>
                <th>Scenario</th>
                <th>Parameters</th>
                <th>Duration (s)</th>
                <th>Status</th>
            </tr>
"""
        )
        for scenario in scenarios:
            name = scenario.get("scenario_name", "unknown")
            params = scenario.get("scenario_params", {})
            params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
            duration_s = scenario.get("duration_seconds", 0)
            success = scenario.get("success", False)
            status_class = "success" if success else "failure"
            status_text = "SUCCESS" if success else "FAILURE"

            html_parts.append(
                f"""
            <tr>
                <td>{name}</td>
                <td>{params_str or "baseline"}</td>
                <td>{duration_s:.2f}</td>
                <td class="{status_class}">{status_text}</td>
            </tr>
"""
            )
        html_parts.append("        </table>\n")

    # Performance charts (if available and requested)
    if chart_engine == "plotly" and scenario_metrics:
        html_parts.append("<h2>Performance Metrics</h2>\n")
        for scenario_name, metrics in scenario_metrics.items():
            chart_html = generate_plotly_charts(metrics, scenario_name)
            if chart_html:
                html_parts.append(
                    f'<div class="chart-container">\n{chart_html}\n</div>\n'
                )
            else:
                html_parts.append(
                    f"<p>Charts not available for scenario: {scenario_name}</p>\n"
                )
    elif chart_engine == "plotly" and not PLOTLY_AVAILABLE:
        html_parts.append(
            "<p><em>Note: Plotly not installed. Charts unavailable.</em></p>\n"
        )

    # Environment information
    env_info = run_manifest.get("environment", {})
    html_parts.append(
        f"""
        <h2>Environment</h2>
        <div class="summary-box">
            <p><strong>Python Version:</strong> {env_info.get("python_version", "unknown")}</p>
            <p><strong>Platform:</strong> {env_info.get("platform", "unknown")}</p>
            <p><strong>Processor:</strong> {env_info.get("processor", "unknown")}</p>
        </div>
"""
    )

    package_versions = env_info.get("package_versions", {})
    if package_versions:
        html_parts.append(
            """
        <h3>Package Versions</h3>
        <table>
            <tr>
                <th>Package</th>
                <th>Version</th>
            </tr>
"""
        )
        for pkg, version in package_versions.items():
            html_parts.append(
                f"""
            <tr>
                <td>{pkg}</td>
                <td>{version}</td>
            </tr>
"""
            )
        html_parts.append("        </table>\n")

    # HTML footer
    html_parts.append(
        """
    </div>
</body>
</html>
"""
    )

    html_content = "".join(html_parts)

    # Write to file if path provided
    if output_path:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"HTML report written to {output_path}")
        except Exception:
            logger.exception(f"Failed to write HTML report to {output_path}")

    return html_content


def create_reports_directory(
    base_output_dir: Path, reports_subdir: str = "reports"
) -> Path:
    """
    Create and return the reports directory path.

    Args:
        base_output_dir: Base output directory (e.g., processed/{site_id}/{year})
        reports_subdir: Subdirectory name for reports (default: "reports")

    Returns:
        Path to the reports directory
    """
    reports_dir = base_output_dir / reports_subdir
    reports_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Reports directory: {reports_dir}")
    return reports_dir
