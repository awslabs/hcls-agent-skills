#!/usr/bin/env python3
"""Filter an annotated VCF using ACMG/AMP classification criteria.

Reads an annotated VCF (with gnomAD AF, ClinVar CLNSIG, REVEL, and CADD
annotations), applies population frequency filtering and ACMG evidence
code collection, assigns pathogenicity tiers, and writes a sorted TSV
of candidate variants.

Usage:
    python filter_by_acmg.py \
        --vcf annotated.vcf.gz \
        --plan plan.json \
        --clinvar clinvar.vcf.gz \
        --gnomad gnomad.vcf.gz \
        --out candidates.tsv

The plan JSON follows the VariantInterpretationPlan schema produced by
the genomic-variant-interpretation reasoning skill.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import pysam


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Required INFO fields in the annotated VCF
REQUIRED_FIELDS = ["gnomAD_AF", "CLNSIG", "REVEL", "CADD_PHRED"]

# Output TSV column order
OUTPUT_COLUMNS = [
    "chrom",
    "pos",
    "ref",
    "alt",
    "gene",
    "consequence",
    "gnomad_af",
    "clinvar_clnsig",
    "revel",
    "cadd",
    "acmg_codes",
    "acmg_tier",
]

# Tier severity ranking (lower number = more severe)
TIER_RANK = {
    "Pathogenic": 0,
    "LikelyPathogenic": 1,
    "VUS": 2,
}

# Loss-of-function consequence types that qualify for PVS1
LOF_CONSEQUENCES = frozenset([
    "stop_gained",
    "frameshift_variant",
    "splice_donor_variant",
    "splice_acceptor_variant",
    "start_lost",
    "stop_lost",
])


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def validate_vcf_fields(vcf_header: pysam.VariantHeader) -> None:
    """Raise an error if the VCF header is missing required INFO fields.

    Args:
        vcf_header: The pysam VariantHeader to validate.

    Raises:
        ValueError: If one or more required fields are absent.
    """
    header_info_keys = set(vcf_header.info)
    missing = [f for f in REQUIRED_FIELDS if f not in header_info_keys]
    if missing:
        raise ValueError(
            f"VCF is missing required annotation fields: {', '.join(missing)}. "
            f"Ensure the VCF has been annotated with VEP/snpEff including "
            f"gnomAD AF, ClinVar CLNSIG, REVEL, and CADD plugins."
        )


def get_info_value(record: pysam.VariantRecord, field: str, default=None):
    """Safely extract an INFO field value from a VCF record.

    Args:
        record: A pysam VariantRecord.
        field: The INFO field name.
        default: Value to return if the field is absent.

    Returns:
        The field value, or default if not present.
    """
    try:
        val = record.info[field]
        # pysam returns tuples for multi-valued fields; take the first
        if isinstance(val, tuple):
            return val[0] if val else default
        return val
    except KeyError:
        return default


def collect_acmg_codes(
    consequence: str,
    clinvar_clnsig: str,
    revel_score: float,
    cadd_score: float,
    computational_thresholds: dict,
) -> list[str]:
    """Collect applicable ACMG evidence codes for a single variant.

    Evaluates three categories of evidence:
    - PVS1: Loss-of-function variants (stop gained, frameshift, splice site)
    - PS1: ClinVar Pathogenic or Likely pathogenic assertion
    - PP3: Computational evidence from REVEL and/or CADD scores

    Args:
        consequence: VEP/snpEff consequence string.
        clinvar_clnsig: ClinVar clinical significance string.
        revel_score: REVEL pathogenicity score (0-1).
        cadd_score: CADD Phred-scaled score.
        computational_thresholds: Dict with "REVEL" and "CADD" threshold keys.

    Returns:
        List of applicable ACMG evidence code strings.
    """
    codes = []

    # PVS1: Null variant (nonsense, frameshift, canonical splice site)
    # in a gene where loss-of-function is a known mechanism of disease
    if consequence in LOF_CONSEQUENCES:
        codes.append("PVS1")

    # PS1: Same amino acid change as an established pathogenic variant
    # Approximated here by ClinVar Pathogenic/Likely_pathogenic assertion
    if clinvar_clnsig and clinvar_clnsig in (
        "Pathogenic",
        "Likely_pathogenic",
        "Pathogenic/Likely_pathogenic",
    ):
        codes.append("PS1")

    # PP3: Computational (in silico) evidence supports a deleterious effect
    revel_threshold = computational_thresholds.get("REVEL", 0.5)
    cadd_threshold = computational_thresholds.get("CADD", 20)
    if revel_score >= revel_threshold or cadd_score >= cadd_threshold:
        codes.append("PP3")

    return codes


def classify_tier(codes: list[str]) -> str | None:
    """Assign an ACMG pathogenicity tier based on collected evidence codes.

    Simplified tier assignment:
    - Pathogenic: PVS1 + at least one supporting code, OR PS1 + PP3
    - LikelyPathogenic: PVS1 alone, OR PS1 alone with no additional support
    - VUS: Any evidence code present but not meeting higher tiers

    Args:
        codes: List of ACMG evidence codes.

    Returns:
        Tier string ("Pathogenic", "LikelyPathogenic", "VUS") or None
        if no evidence codes are present.
    """
    if not codes:
        return None

    has_pvs1 = "PVS1" in codes
    has_ps1 = "PS1" in codes
    has_pp3 = "PP3" in codes

    # Pathogenic: strong + supporting evidence combinations
    if has_pvs1 and (has_ps1 or has_pp3):
        return "Pathogenic"
    if has_ps1 and has_pp3:
        return "Pathogenic"

    # LikelyPathogenic: single strong evidence
    if has_pvs1 or has_ps1:
        return "LikelyPathogenic"

    # VUS: some evidence but insufficient for higher classification
    return "VUS"


def load_plan(plan_path: str) -> dict:
    """Load and validate a VariantInterpretationPlan from a JSON file.

    Args:
        plan_path: Path to the JSON plan file.

    Returns:
        Parsed plan dictionary.

    Raises:
        FileNotFoundError: If the plan file does not exist.
        ValueError: If required plan fields are missing.
    """
    path = Path(plan_path)
    if not path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")

    with open(path) as f:
        plan = json.load(f)

    # Validate required fields
    if "population_af_threshold" not in plan:
        raise ValueError("Plan JSON missing required field: population_af_threshold")
    if "computational_thresholds" not in plan:
        raise ValueError("Plan JSON missing required field: computational_thresholds")

    return plan


# ---------------------------------------------------------------------------
# Main filtering logic
# ---------------------------------------------------------------------------

def filter_variants(
    vcf_path: str,
    plan: dict,
    clinvar_vcf: str,
    gnomad_vcf: str,
    output_tsv: str,
) -> None:
    """Filter an annotated VCF down to candidates matching the ACMG plan.

    Streams the VCF record-by-record using pysam (no full load into memory).
    For each variant, applies population frequency filtering, collects ACMG
    evidence codes, assigns a pathogenicity tier, and writes qualifying
    variants to a TSV sorted by tier severity then gene symbol.

    Args:
        vcf_path: Path to the annotated, normalized VCF.
        plan: VariantInterpretationPlan dict with population_af_threshold
              and computational_thresholds.
        clinvar_vcf: Path to ClinVar VCF (used for reference; annotations
                     are expected in the input VCF INFO fields).
        gnomad_vcf: Path to gnomAD VCF (used for reference; annotations
                    are expected in the input VCF INFO fields).
        output_tsv: Path for the output TSV file.
    """
    af_threshold = plan["population_af_threshold"]
    comp_thresholds = plan.get("computational_thresholds", {"REVEL": 0.5, "CADD": 20})

    # Open the annotated VCF and validate required fields
    vcf_in = pysam.VariantFile(vcf_path)
    validate_vcf_fields(vcf_in.header)

    candidates = []

    # Stream through VCF records one at a time
    for record in vcf_in:
        # Extract annotation values from INFO fields
        gnomad_af = get_info_value(record, "gnomAD_AF", default=0.0)
        if isinstance(gnomad_af, str):
            try:
                gnomad_af = float(gnomad_af)
            except (ValueError, TypeError):
                gnomad_af = 0.0

        # Step 1: Population frequency filter
        # Skip common variants above the AF threshold
        if gnomad_af > af_threshold:
            continue

        clinvar_clnsig = get_info_value(record, "CLNSIG", default="")
        if isinstance(clinvar_clnsig, (tuple, list)):
            clinvar_clnsig = str(clinvar_clnsig[0]) if clinvar_clnsig else ""
        else:
            clinvar_clnsig = str(clinvar_clnsig) if clinvar_clnsig else ""

        revel = get_info_value(record, "REVEL", default=0.0)
        try:
            revel = float(revel)
        except (ValueError, TypeError):
            revel = 0.0

        cadd = get_info_value(record, "CADD_PHRED", default=0.0)
        try:
            cadd = float(cadd)
        except (ValueError, TypeError):
            cadd = 0.0

        # Extract gene and consequence (CSQ or ANN field, or direct INFO)
        gene = get_info_value(record, "SYMBOL", default="")
        if not gene:
            gene = get_info_value(record, "Gene", default="unknown")
        gene = str(gene) if gene else "unknown"

        consequence = get_info_value(record, "Consequence", default="")
        if not consequence:
            consequence = get_info_value(record, "ANN", default="unknown")
        consequence = str(consequence) if consequence else "unknown"

        # Step 2: Collect ACMG evidence codes
        codes = collect_acmg_codes(
            consequence=consequence,
            clinvar_clnsig=clinvar_clnsig,
            revel_score=revel,
            cadd_score=cadd,
            computational_thresholds=comp_thresholds,
        )

        # Step 3: Assign tier
        tier = classify_tier(codes)

        # Only keep variants classified as VUS or more severe
        if tier is not None and tier in TIER_RANK:
            # Process each ALT allele
            for alt in record.alts or []:
                candidates.append({
                    "chrom": record.chrom,
                    "pos": record.pos,
                    "ref": record.ref,
                    "alt": alt,
                    "gene": gene,
                    "consequence": consequence,
                    "gnomad_af": f"{gnomad_af:.6f}",
                    "clinvar_clnsig": clinvar_clnsig,
                    "revel": f"{revel:.4f}",
                    "cadd": f"{cadd:.2f}",
                    "acmg_codes": ";".join(codes) if codes else ".",
                    "acmg_tier": tier,
                })

    vcf_in.close()

    # Sort by tier severity (Pathogenic first), then by gene symbol
    candidates.sort(key=lambda c: (TIER_RANK.get(c["acmg_tier"], 99), c["gene"]))

    # Write output TSV
    with open(output_tsv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(candidates)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse command-line arguments and run the ACMG filtering pipeline."""
    parser = argparse.ArgumentParser(
        description=(
            "Filter an annotated VCF using ACMG/AMP classification criteria. "
            "Produces a TSV of candidate variants with evidence codes and "
            "pathogenicity tiers."
        ),
    )
    parser.add_argument(
        "--vcf",
        required=True,
        help="Path to the annotated VCF file (must include gnomAD_AF, CLNSIG, REVEL, CADD_PHRED annotations).",
    )
    parser.add_argument(
        "--plan",
        required=True,
        help="Path to the VariantInterpretationPlan JSON file.",
    )
    parser.add_argument(
        "--clinvar",
        required=True,
        help="Path to the ClinVar VCF file (GRCh38 build).",
    )
    parser.add_argument(
        "--gnomad",
        required=True,
        help="Path to the gnomAD VCF file (GRCh38 build).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path for the output TSV file.",
    )

    args = parser.parse_args()

    # Load the interpretation plan
    plan = load_plan(args.plan)

    # Run the filtering pipeline
    filter_variants(
        vcf_path=args.vcf,
        plan=plan,
        clinvar_vcf=args.clinvar,
        gnomad_vcf=args.gnomad,
        output_tsv=args.out,
    )

    print(f"Wrote candidate variants to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
