#!/usr/bin/env python3
"""Run a DESeq2 differential expression contrast using pyDESeq2.

Reads a gene-level counts matrix (genes x samples) and sample metadata,
applies independent filtering, runs DESeq2 with the specified contrast,
applies LFC shrinkage, and writes results sorted by adjusted p-value.

Usage:
    python deseq2_contrast.py \
        --counts gene_counts.tsv \
        --coldata sample_metadata.tsv \
        --contrast "condition:treated:control" \
        --output results.tsv

The counts TSV should have gene IDs as the first column and one column per
sample with raw (unnormalized) integer counts. The coldata TSV should have
sample IDs as the first column and metadata columns including the factor
used in the contrast.

This script uses pyDESeq2, a pure-Python implementation of the DESeq2
method. For the original R implementation, use the DESeq2 Bioconductor
package with the equivalent workflow shown in the SKILL.md file.

Alternative approach using rpy2 (R's DESeq2 via Python):
    If you prefer the original R DESeq2 engine, install rpy2 and
    bioconductor-deseq2, then replace the pyDESeq2 calls below with:
        import rpy2.robjects as ro
        from rpy2.robjects import pandas2ri
        pandas2ri.activate()
        ro.r('library(DESeq2)')
        # Transfer counts and coldata to R, run DESeqDataSetFromMatrix, etc.
    This approach gives identical results to running DESeq2 in R directly.

Dependencies:
    pip install pydeseq2 pandas
"""

import argparse
import sys

import pandas as pd


def parse_contrast(contrast_str: str) -> tuple[str, str, str]:
    """Parse a contrast string in the format 'factor:numerator:denominator'.

    Args:
        contrast_str: Colon-separated contrast specification.

    Returns:
        Tuple of (factor, numerator, denominator).

    Raises:
        ValueError: If the contrast string does not have exactly 3 parts.
    """
    parts = contrast_str.split(":")
    if len(parts) != 3:
        raise ValueError(
            f"Contrast must be 'factor:numerator:denominator', got '{contrast_str}'"
        )
    return parts[0], parts[1], parts[2]


def load_counts(path: str) -> pd.DataFrame:
    """Load a counts matrix from a TSV file.

    Expects genes as rows and samples as columns. The first column is
    treated as the gene ID index. Lines starting with '#' are skipped
    (featureCounts adds a comment header).

    Args:
        path: Path to the counts TSV file.

    Returns:
        DataFrame with gene IDs as index and samples as columns.
    """
    df = pd.read_csv(path, sep="\t", index_col=0, comment="#")
    # featureCounts includes Chr, Start, End, Strand, Length columns before
    # the count columns. Drop any non-numeric columns.
    numeric_cols = df.select_dtypes(include="number").columns
    return df[numeric_cols].astype(int)


def load_coldata(path: str) -> pd.DataFrame:
    """Load sample metadata from a TSV file.

    The first column is treated as the sample ID index.

    Args:
        path: Path to the coldata TSV file.

    Returns:
        DataFrame with sample IDs as index and metadata columns.
    """
    return pd.read_csv(path, sep="\t", index_col=0)


def run_deseq2_contrast(
    counts_df: pd.DataFrame,
    coldata_df: pd.DataFrame,
    factor: str,
    numerator: str,
    denominator: str,
    min_count: int = 10,
) -> pd.DataFrame:
    """Run DESeq2 differential expression with a specified contrast.

    Args:
        counts_df: Raw counts matrix (genes x samples).
        coldata_df: Sample metadata with at least the contrast factor column.
        factor: The metadata column to test (e.g., 'condition').
        numerator: The treatment/test level (e.g., 'treated').
        denominator: The reference/control level (e.g., 'control').
        min_count: Minimum total count across samples to keep a gene.

    Returns:
        DataFrame with DESeq2 results sorted by padj, containing columns:
        gene, baseMean, log2FoldChange, lfcSE, stat, pvalue, padj.
    """
    # Import pydeseq2 here so the module can be imported without it installed
    # (useful for documentation and testing of the CLI parsing)
    from pydeseq2.dds import DeseqDataSet
    from pydeseq2.ds import DeseqStats

    # Validate that the factor column exists in coldata
    if factor not in coldata_df.columns:
        raise ValueError(
            f"Factor '{factor}' not found in coldata columns: "
            f"{list(coldata_df.columns)}"
        )

    # Validate that numerator and denominator levels exist
    levels = coldata_df[factor].unique()
    for level, label in [(numerator, "numerator"), (denominator, "denominator")]:
        if level not in levels:
            raise ValueError(
                f"Contrast {label} '{level}' not found in factor '{factor}' "
                f"levels: {list(levels)}"
            )

    # Align samples between counts and coldata
    shared_samples = counts_df.columns.intersection(coldata_df.index)
    if len(shared_samples) == 0:
        raise ValueError(
            "No shared sample IDs between counts columns and coldata index. "
            "Check that sample names match."
        )
    counts_aligned = counts_df[shared_samples]
    coldata_aligned = coldata_df.loc[shared_samples]

    # Independent filtering: remove genes with low total counts
    gene_sums = counts_aligned.sum(axis=1)
    keep = gene_sums >= min_count
    counts_filtered = counts_aligned[keep]

    if counts_filtered.shape[0] == 0:
        raise ValueError(
            f"No genes remain after filtering with min_count={min_count}. "
            "Try lowering --min-count."
        )

    # pyDESeq2 expects samples as rows and genes as columns
    counts_T = counts_filtered.T

    # Build design and run DESeq2
    dds = DeseqDataSet(
        counts=counts_T,
        metadata=coldata_aligned,
        design=f"~ {factor}",
    )
    dds.deseq2()

    # Run statistical test with the specified contrast
    stat_res = DeseqStats(
        dds,
        contrast=[factor, numerator, denominator],
    )
    stat_res.summary()

    # Apply LFC shrinkage for more accurate fold change estimates
    # pyDESeq2 supports apeglm-style shrinkage via lfc_shrink()
    stat_res.lfc_shrink(coeff=f"{factor}_{numerator}_vs_{denominator}")

    # Extract results and format output
    results_df = stat_res.results_df.copy()
    results_df.index.name = "gene"
    results_df = results_df.reset_index()

    # Select and rename columns to match the expected output format
    output_cols = ["gene", "baseMean", "log2FoldChange", "lfcSE", "stat", "pvalue", "padj"]
    # Ensure all expected columns are present
    for col in output_cols:
        if col not in results_df.columns:
            results_df[col] = float("nan")

    results_df = results_df[output_cols]

    # Sort by adjusted p-value (NaN values last)
    results_df = results_df.sort_values("padj", na_position="last")

    return results_df


def main() -> None:
    """Entry point for the DESeq2 contrast script."""
    parser = argparse.ArgumentParser(
        description="Run DESeq2 differential expression contrast using pyDESeq2.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python deseq2_contrast.py \\\n"
            "    --counts gene_counts.tsv \\\n"
            "    --coldata sample_metadata.tsv \\\n"
            "    --contrast condition:treated:control \\\n"
            "    --output results.tsv\n"
        ),
    )
    parser.add_argument(
        "--counts",
        required=True,
        help="Path to counts matrix TSV (genes x samples, first column = gene ID).",
    )
    parser.add_argument(
        "--coldata",
        required=True,
        help="Path to sample metadata TSV (first column = sample ID).",
    )
    parser.add_argument(
        "--contrast",
        required=True,
        help="Contrast specification as 'factor:numerator:denominator' "
        "(e.g., 'condition:treated:control').",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the results TSV.",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=10,
        help="Minimum total count across samples to keep a gene (default: 10).",
    )

    args = parser.parse_args()

    # Parse contrast specification
    try:
        factor, numerator, denominator = parse_contrast(args.contrast)
    except ValueError as e:
        parser.error(str(e))

    # Load input data
    print(f"Loading counts from {args.counts}...")
    counts_df = load_counts(args.counts)
    print(f"  Loaded {counts_df.shape[0]} genes x {counts_df.shape[1]} samples")

    print(f"Loading sample metadata from {args.coldata}...")
    coldata_df = load_coldata(args.coldata)
    print(f"  Loaded {coldata_df.shape[0]} samples x {coldata_df.shape[1]} columns")

    # Run DESeq2
    print(f"Running DESeq2 contrast: {factor} ({numerator} vs {denominator})...")
    print(f"  Independent filtering: min_count = {args.min_count}")
    results_df = run_deseq2_contrast(
        counts_df=counts_df,
        coldata_df=coldata_df,
        factor=factor,
        numerator=numerator,
        denominator=denominator,
        min_count=args.min_count,
    )

    # Write results
    results_df.to_csv(args.output, sep="\t", index=False)
    print(f"Wrote {len(results_df)} genes to {args.output}")

    # Summary statistics
    if "padj" in results_df.columns:
        sig_005 = (results_df["padj"] < 0.05).sum()
        sig_001 = (results_df["padj"] < 0.01).sum()
        print(f"  Significant genes (padj < 0.05): {sig_005}")
        print(f"  Significant genes (padj < 0.01): {sig_001}")


if __name__ == "__main__":
    main()
