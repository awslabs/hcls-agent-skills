#!/usr/bin/env python3
"""Aggregate NGS QC metrics into a self-contained HTML report.

Parses FastQC summary files, samtools flagstat output, and optionally
Picard insert size metrics to produce a single HTML report with
pass/warn/fail status per sample based on configurable thresholds.

Usage:
    python qc_report.py \
        --fastqc-dir qc/fastqc_raw/ \
        --flagstat qc/samtools/sample1.flagstat.txt qc/samtools/sample2.flagstat.txt \
        --picard qc/picard/sample1.insert_size_metrics.txt \
        --output qc/summary_report.html \
        --q30-threshold 0.8 \
        --dup-threshold 0.3

Thresholds:
    --q30-threshold: Minimum fraction of bases with quality >= Q30 (default 0.8)
    --dup-threshold: Maximum duplication rate as a fraction (default 0.3)

The report documents all thresholds used so results are reproducible.
"""

import argparse
import os
import re
import sys
from pathlib import Path


def parse_args(argv=None):
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:] if None).

    Returns:
        argparse.Namespace with parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Aggregate NGS QC metrics into a self-contained HTML report."
    )
    parser.add_argument(
        "--fastqc-dir",
        required=True,
        help="Directory containing FastQC output folders (each with summary.txt or fastqc_data.txt).",
    )
    parser.add_argument(
        "--flagstat",
        required=True,
        nargs="+",
        help="One or more samtools flagstat output files.",
    )
    parser.add_argument(
        "--picard",
        nargs="+",
        default=None,
        help="Optional Picard CollectInsertSizeMetrics output files.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for the HTML report.",
    )
    parser.add_argument(
        "--q30-threshold",
        type=float,
        default=0.8,
        help="Minimum Q30 fraction to pass (default: 0.8).",
    )
    parser.add_argument(
        "--dup-threshold",
        type=float,
        default=0.3,
        help="Maximum duplication rate to pass (default: 0.3).",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# FastQC parsing
# ---------------------------------------------------------------------------

def parse_fastqc_summary(fastqc_dir):
    """Parse FastQC summary files from a directory of FastQC outputs.

    Looks for ``summary.txt`` (tab-delimited: status, module, filename) or
    falls back to ``fastqc_data.txt`` in each sample's output folder.

    Args:
        fastqc_dir: Path to the directory containing per-sample FastQC
            output folders (e.g., ``sample1_R1_fastqc/``).

    Returns:
        dict mapping sample name to a dict of module statuses, e.g.::

            {"sample1_R1": {"Per base sequence quality": "PASS", ...}}
    """
    results = {}
    fastqc_path = Path(fastqc_dir)

    if not fastqc_path.is_dir():
        print(f"Warning: FastQC directory not found: {fastqc_dir}", file=sys.stderr)
        return results

    for entry in sorted(fastqc_path.iterdir()):
        # Each FastQC output is a folder ending in _fastqc
        if not entry.is_dir():
            continue

        sample_name = entry.name.replace("_fastqc", "")
        summary_file = entry / "summary.txt"
        data_file = entry / "fastqc_data.txt"

        if summary_file.exists():
            results[sample_name] = _parse_summary_txt(summary_file)
        elif data_file.exists():
            results[sample_name] = _parse_fastqc_data(data_file)

    return results


def _parse_summary_txt(path):
    """Parse a FastQC summary.txt file.

    Each line is tab-delimited: STATUS \\t MODULE_NAME \\t FILENAME

    Returns:
        dict mapping module name to status string (PASS/WARN/FAIL).
    """
    modules = {}
    with open(path, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                status = parts[0].upper()
                module_name = parts[1]
                modules[module_name] = status
    return modules


def _parse_fastqc_data(path):
    """Parse a FastQC fastqc_data.txt file for module pass/warn/fail status.

    Module headers look like: ``>>Per base sequence quality\\tpass``

    Returns:
        dict mapping module name to status string (PASS/WARN/FAIL).
    """
    modules = {}
    with open(path, "r") as fh:
        for line in fh:
            if line.startswith(">>") and not line.startswith(">>END_MODULE"):
                parts = line.strip().lstrip(">>").split("\t")
                if len(parts) >= 2:
                    module_name = parts[0]
                    status = parts[1].upper()
                    modules[module_name] = status
    return modules


def extract_q30_from_fastqc(fastqc_dir):
    """Extract Q30 fraction from FastQC per-sequence quality data.

    Reads the ``Per sequence quality scores`` section of fastqc_data.txt
    to compute the fraction of reads with mean quality >= 30.

    Args:
        fastqc_dir: Path to the directory containing per-sample FastQC
            output folders.

    Returns:
        dict mapping sample name to Q30 fraction (float 0.0–1.0).
    """
    q30_fractions = {}
    fastqc_path = Path(fastqc_dir)

    if not fastqc_path.is_dir():
        return q30_fractions

    for entry in sorted(fastqc_path.iterdir()):
        if not entry.is_dir():
            continue

        sample_name = entry.name.replace("_fastqc", "")
        data_file = entry / "fastqc_data.txt"

        if not data_file.exists():
            continue

        # Parse the per-sequence quality scores section
        in_section = False
        total_count = 0
        q30_count = 0

        with open(data_file, "r") as fh:
            for line in fh:
                if line.startswith(">>Per sequence quality scores"):
                    in_section = True
                    continue
                if in_section and line.startswith(">>END_MODULE"):
                    break
                if in_section and not line.startswith("#"):
                    parts = line.strip().split("\t")
                    if len(parts) == 2:
                        try:
                            quality = int(float(parts[0]))
                            count = float(parts[1])
                            total_count += count
                            if quality >= 30:
                                q30_count += count
                        except ValueError:
                            continue

        if total_count > 0:
            q30_fractions[sample_name] = q30_count / total_count

    return q30_fractions


# ---------------------------------------------------------------------------
# samtools flagstat parsing
# ---------------------------------------------------------------------------

def parse_flagstat(flagstat_path):
    """Parse a samtools flagstat output file.

    Extracts total reads, mapped reads, duplicates, and properly paired
    counts from the standard flagstat format.

    Args:
        flagstat_path: Path to a samtools flagstat output file.

    Returns:
        dict with keys: sample, total_reads, mapped_reads, duplicates,
        properly_paired, mapped_pct, dup_rate, properly_paired_pct.
    """
    sample_name = Path(flagstat_path).stem.replace(".flagstat", "")
    metrics = {
        "sample": sample_name,
        "total_reads": 0,
        "mapped_reads": 0,
        "duplicates": 0,
        "properly_paired": 0,
    }

    with open(flagstat_path, "r") as fh:
        for line in fh:
            line = line.strip()
            # Total reads (QC-passed): "12345 + 0 in total"
            match = re.match(r"(\d+)\s+\+\s+\d+\s+in total", line)
            if match:
                metrics["total_reads"] = int(match.group(1))
                continue

            # Mapped reads: "12000 + 0 mapped"
            match = re.match(r"(\d+)\s+\+\s+\d+\s+mapped\s", line)
            if match:
                metrics["mapped_reads"] = int(match.group(1))
                continue

            # Duplicates: "500 + 0 duplicates"
            match = re.match(r"(\d+)\s+\+\s+\d+\s+duplicates", line)
            if match:
                metrics["duplicates"] = int(match.group(1))
                continue

            # Properly paired: "11000 + 0 properly paired"
            match = re.match(r"(\d+)\s+\+\s+\d+\s+properly paired", line)
            if match:
                metrics["properly_paired"] = int(match.group(1))
                continue

    # Compute derived metrics
    total = metrics["total_reads"]
    if total > 0:
        metrics["mapped_pct"] = metrics["mapped_reads"] / total
        metrics["dup_rate"] = metrics["duplicates"] / total
        metrics["properly_paired_pct"] = metrics["properly_paired"] / total
    else:
        metrics["mapped_pct"] = 0.0
        metrics["dup_rate"] = 0.0
        metrics["properly_paired_pct"] = 0.0

    return metrics


# ---------------------------------------------------------------------------
# Picard insert size parsing
# ---------------------------------------------------------------------------

def parse_picard_insert_size(picard_path):
    """Parse a Picard CollectInsertSizeMetrics output file.

    Reads the metrics table (after the ``## METRICS CLASS`` header) to
    extract median and mean insert sizes.

    Args:
        picard_path: Path to a Picard insert size metrics file.

    Returns:
        dict with keys: sample, median_insert_size, mean_insert_size,
        standard_deviation. Returns None if parsing fails.
    """
    sample_name = Path(picard_path).stem.replace(".insert_size_metrics", "")
    metrics = {"sample": sample_name}

    with open(picard_path, "r") as fh:
        lines = fh.readlines()

    # Find the METRICS CLASS header line
    header_idx = None
    for i, line in enumerate(lines):
        if line.startswith("## METRICS CLASS"):
            header_idx = i
            break

    if header_idx is None or header_idx + 2 >= len(lines):
        return None

    # The next line is the column header, the line after is the first data row
    columns = lines[header_idx + 1].strip().split("\t")
    values = lines[header_idx + 2].strip().split("\t")

    col_map = dict(zip(columns, values))

    try:
        metrics["median_insert_size"] = float(col_map.get("MEDIAN_INSERT_SIZE", 0))
        metrics["mean_insert_size"] = float(col_map.get("MEAN_INSERT_SIZE", 0))
        metrics["standard_deviation"] = float(
            col_map.get("STANDARD_DEVIATION", 0)
        )
    except (ValueError, TypeError):
        return None

    return metrics


# ---------------------------------------------------------------------------
# Status assignment
# ---------------------------------------------------------------------------

def assign_status(value, pass_threshold, warn_threshold, higher_is_better=True):
    """Assign pass/warn/fail status based on a metric value and thresholds.

    Args:
        value: The metric value to evaluate.
        pass_threshold: Threshold for PASS status.
        warn_threshold: Threshold for WARN status (between PASS and FAIL).
        higher_is_better: If True, values above pass_threshold are PASS.
            If False, values below pass_threshold are PASS.

    Returns:
        One of "PASS", "WARN", or "FAIL".
    """
    if value is None:
        return "N/A"

    if higher_is_better:
        if value >= pass_threshold:
            return "PASS"
        elif value >= warn_threshold:
            return "WARN"
        else:
            return "FAIL"
    else:
        # Lower is better (e.g., duplication rate)
        if value <= pass_threshold:
            return "PASS"
        elif value <= warn_threshold:
            return "WARN"
        else:
            return "FAIL"


# ---------------------------------------------------------------------------
# HTML report generation
# ---------------------------------------------------------------------------

def generate_html_report(
    flagstat_metrics,
    fastqc_summaries,
    q30_fractions,
    picard_metrics,
    q30_threshold,
    dup_threshold,
    output_path,
):
    """Generate a self-contained HTML report with per-sample QC status.

    Args:
        flagstat_metrics: List of dicts from parse_flagstat().
        fastqc_summaries: Dict from parse_fastqc_summary().
        q30_fractions: Dict from extract_q30_from_fastqc().
        picard_metrics: List of dicts from parse_picard_insert_size() or None.
        q30_threshold: Minimum Q30 fraction for PASS.
        dup_threshold: Maximum duplication rate for PASS.
        output_path: Path to write the HTML report.
    """
    # Build a lookup for Picard metrics by sample name
    picard_lookup = {}
    if picard_metrics:
        for pm in picard_metrics:
            if pm is not None:
                picard_lookup[pm["sample"]] = pm

    # Build per-sample rows
    rows = []
    for fm in flagstat_metrics:
        sample = fm["sample"]
        total_reads = fm["total_reads"]
        mapped_pct = fm["mapped_pct"]
        dup_rate = fm["dup_rate"]
        properly_paired_pct = fm["properly_paired_pct"]

        # Q30 fraction from FastQC (may not be available for all samples)
        q30 = q30_fractions.get(sample)

        # Insert size from Picard (optional)
        insert_size = None
        if sample in picard_lookup:
            insert_size = picard_lookup[sample].get("mean_insert_size")

        # Assign statuses
        q30_status = assign_status(q30, q30_threshold, q30_threshold * 0.875, higher_is_better=True)
        dup_status = assign_status(dup_rate, dup_threshold, dup_threshold * 1.67, higher_is_better=False)
        mapped_status = assign_status(mapped_pct, 0.95, 0.90, higher_is_better=True)
        paired_status = assign_status(properly_paired_pct, 0.90, 0.80, higher_is_better=True)

        # Overall sample status: FAIL if any metric fails, WARN if any warns
        statuses = [q30_status, dup_status, mapped_status, paired_status]
        if "FAIL" in statuses:
            overall = "FAIL"
        elif "WARN" in statuses:
            overall = "WARN"
        else:
            overall = "PASS"

        rows.append({
            "sample": sample,
            "total_reads": total_reads,
            "mapped_pct": mapped_pct,
            "q30": q30,
            "dup_rate": dup_rate,
            "properly_paired_pct": properly_paired_pct,
            "insert_size": insert_size,
            "q30_status": q30_status,
            "dup_status": dup_status,
            "mapped_status": mapped_status,
            "paired_status": paired_status,
            "overall": overall,
        })

    # Generate HTML
    html = _build_html(rows, q30_threshold, dup_threshold)

    # Write output
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w") as fh:
        fh.write(html)

    print(f"Report written to {output_path}")


def _status_class(status):
    """Return a CSS class name for a status string."""
    return {
        "PASS": "pass",
        "WARN": "warn",
        "FAIL": "fail",
    }.get(status, "na")


def _fmt_pct(value):
    """Format a fraction as a percentage string."""
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def _fmt_number(value):
    """Format an integer with comma separators."""
    if value is None:
        return "N/A"
    return f"{value:,}"


def _build_html(rows, q30_threshold, dup_threshold):
    """Build the complete self-contained HTML report string.

    Args:
        rows: List of per-sample metric dicts.
        q30_threshold: Q30 threshold used for status assignment.
        dup_threshold: Duplication rate threshold used for status assignment.

    Returns:
        Complete HTML string.
    """
    # Build table rows
    table_rows = []
    for r in rows:
        overall_cls = _status_class(r["overall"])
        insert_cell = (
            f'<td>{r["insert_size"]:.1f} bp</td>'
            if r["insert_size"] is not None
            else '<td class="na">N/A</td>'
        )
        table_rows.append(
            f'<tr>'
            f'<td>{r["sample"]}</td>'
            f'<td>{_fmt_number(r["total_reads"])}</td>'
            f'<td class="{_status_class(r["mapped_status"])}">{_fmt_pct(r["mapped_pct"])}</td>'
            f'<td class="{_status_class(r["q30_status"])}">{_fmt_pct(r["q30"])}</td>'
            f'<td class="{_status_class(r["dup_status"])}">{_fmt_pct(r["dup_rate"])}</td>'
            f'<td class="{_status_class(r["paired_status"])}">{_fmt_pct(r["properly_paired_pct"])}</td>'
            f'{insert_cell}'
            f'<td class="{overall_cls}">{r["overall"]}</td>'
            f"</tr>"
        )

    table_body = "\n        ".join(table_rows)

    # Count summary
    total_samples = len(rows)
    pass_count = sum(1 for r in rows if r["overall"] == "PASS")
    warn_count = sum(1 for r in rows if r["overall"] == "WARN")
    fail_count = sum(1 for r in rows if r["overall"] == "FAIL")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NGS QC Summary Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 2rem;
            background: #fafafa;
            color: #333;
        }}
        h1 {{ color: #2c3e50; }}
        h2 {{ color: #34495e; margin-top: 2rem; }}
        .summary {{
            display: flex;
            gap: 1rem;
            margin: 1rem 0;
        }}
        .summary-card {{
            padding: 1rem 1.5rem;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.1rem;
        }}
        .summary-pass {{ background: #d4edda; color: #155724; }}
        .summary-warn {{ background: #fff3cd; color: #856404; }}
        .summary-fail {{ background: #f8d7da; color: #721c24; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 0.6rem 1rem;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #2c3e50;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{ background: #f5f5f5; }}
        .pass {{ color: #155724; }}
        .warn {{ color: #856404; }}
        .fail {{ color: #721c24; font-weight: bold; }}
        .na {{ color: #999; }}
        .thresholds {{
            background: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }}
        .thresholds table {{ box-shadow: none; }}
    </style>
</head>
<body>
    <h1>NGS QC Summary Report</h1>

    <div class="summary">
        <div class="summary-card summary-pass">PASS: {pass_count}</div>
        <div class="summary-card summary-warn">WARN: {warn_count}</div>
        <div class="summary-card summary-fail">FAIL: {fail_count}</div>
        <div class="summary-card" style="background:#e2e3e5;color:#383d41;">Total: {total_samples}</div>
    </div>

    <h2>Per-Sample Metrics</h2>
    <table>
        <thead>
            <tr>
                <th>Sample</th>
                <th>Total Reads</th>
                <th>Mapped %</th>
                <th>Q30 %</th>
                <th>Duplication %</th>
                <th>Properly Paired %</th>
                <th>Mean Insert Size</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
        {table_body}
        </tbody>
    </table>

    <h2>Thresholds Used</h2>
    <div class="thresholds">
        <p>Samples are classified as PASS, WARN, or FAIL based on the following thresholds.
        A sample receives an overall FAIL if any individual metric fails.</p>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>PASS</th>
                    <th>WARN</th>
                    <th>FAIL</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Q30 fraction</td>
                    <td>&ge; {q30_threshold * 100:.0f}%</td>
                    <td>{q30_threshold * 87.5:.0f}% &ndash; {q30_threshold * 100:.0f}%</td>
                    <td>&lt; {q30_threshold * 87.5:.0f}%</td>
                </tr>
                <tr>
                    <td>Duplication rate</td>
                    <td>&le; {dup_threshold * 100:.0f}%</td>
                    <td>{dup_threshold * 100:.0f}% &ndash; {dup_threshold * 167:.0f}%</td>
                    <td>&gt; {dup_threshold * 167:.0f}%</td>
                </tr>
                <tr>
                    <td>Mapping rate</td>
                    <td>&ge; 95%</td>
                    <td>90% &ndash; 95%</td>
                    <td>&lt; 90%</td>
                </tr>
                <tr>
                    <td>Properly paired rate</td>
                    <td>&ge; 90%</td>
                    <td>80% &ndash; 90%</td>
                    <td>&lt; 80%</td>
                </tr>
            </tbody>
        </table>
    </div>

    <footer style="margin-top:2rem;color:#999;font-size:0.85rem;">
        Generated by ngs-quality-control/scripts/qc_report.py
    </footer>
</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    """Main entry point for the QC report generator."""
    args = parse_args(argv)

    # Parse FastQC summaries and Q30 fractions
    fastqc_summaries = parse_fastqc_summary(args.fastqc_dir)
    q30_fractions = extract_q30_from_fastqc(args.fastqc_dir)

    # Parse flagstat files
    flagstat_metrics = []
    for fpath in args.flagstat:
        flagstat_metrics.append(parse_flagstat(fpath))

    # Parse optional Picard insert size metrics
    picard_metrics = None
    if args.picard:
        picard_metrics = []
        for ppath in args.picard:
            result = parse_picard_insert_size(ppath)
            if result is not None:
                picard_metrics.append(result)

    # Generate the HTML report
    generate_html_report(
        flagstat_metrics=flagstat_metrics,
        fastqc_summaries=fastqc_summaries,
        q30_fractions=q30_fractions,
        picard_metrics=picard_metrics,
        q30_threshold=args.q30_threshold,
        dup_threshold=args.dup_threshold,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
