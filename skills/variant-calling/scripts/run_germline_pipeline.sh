#!/usr/bin/env bash
# =============================================================================
# run_germline_pipeline.sh
#
# End-to-end germline short-variant calling pipeline:
#   FASTQ → BWA-MEM2 → sort → markdup → BQSR → HaplotypeCaller → VEP → filter
#
# Demonstrates the GATK best-practices workflow for a single sample.
# For multi-sample joint calling, run steps 1-6 per sample, then use
# GenomicsDBImport + GenotypeGVCFs + VQSR on the combined GVCFs.
#
# Dependencies: BWA-MEM2 >=2.2, GATK4 >=4.4, SAMtools >=1.17,
#               bcftools >=1.17, VEP >=110, Python 3.10+ with pysam
#
# Example using public GATK test data:
#   bash run_germline_pipeline.sh \
#       NA12878 \
#       /data/NA12878_R1.fastq.gz \
#       /data/NA12878_R2.fastq.gz \
#       /refs/GRCh38.fa \
#       /output/NA12878
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
Usage: $(basename "$0") SAMPLE_ID FASTQ_R1 FASTQ_R2 REFERENCE OUTPUT_DIR

Positional arguments:
  SAMPLE_ID    Sample identifier (used for read group and output naming)
  FASTQ_R1     Path to forward reads (FASTQ, optionally gzipped)
  FASTQ_R2     Path to reverse reads (FASTQ, optionally gzipped)
  REFERENCE    Path to the indexed GRCh38 reference FASTA
  OUTPUT_DIR   Directory for all output files (created if it does not exist)

Environment variables (optional):
  THREADS      Number of CPU threads to use (default: 8)
  JAVA_MEM     JVM heap size for GATK (default: 16g)
  KNOWN_SITES  Path to known-sites VCF for BQSR (default: refs/dbsnp_146.hg38.vcf.gz)
  VEP_CACHE    Path to VEP cache directory (default: \$HOME/.vep)

Example:
  THREADS=16 JAVA_MEM=32g bash $(basename "$0") \\
      NA12878 reads_R1.fq.gz reads_R2.fq.gz refs/GRCh38.fa output/
EOF
    exit 1
}

# ---------------------------------------------------------------------------
# Parse positional arguments
# ---------------------------------------------------------------------------
if [[ $# -ne 5 ]]; then
    echo "Error: expected 5 arguments, got $#" >&2
    usage
fi

SAMPLE_ID="$1"
FASTQ_R1="$2"
FASTQ_R2="$3"
REFERENCE="$4"
OUTPUT_DIR="$5"

# Configurable defaults via environment variables
THREADS="${THREADS:-8}"
JAVA_MEM="${JAVA_MEM:-16g}"
KNOWN_SITES="${KNOWN_SITES:-refs/dbsnp_146.hg38.vcf.gz}"
VEP_CACHE="${VEP_CACHE:-$HOME/.vep}"

# ---------------------------------------------------------------------------
# Validate inputs
# ---------------------------------------------------------------------------
for f in "$FASTQ_R1" "$FASTQ_R2" "$REFERENCE"; do
    if [[ ! -f "$f" ]]; then
        echo "Error: file not found: $f" >&2
        exit 1
    fi
done

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "=== Germline Variant Calling Pipeline ==="
echo "Sample:    $SAMPLE_ID"
echo "Reads:     $FASTQ_R1, $FASTQ_R2"
echo "Reference: $REFERENCE"
echo "Output:    $OUTPUT_DIR"
echo "Threads:   $THREADS"
echo "JVM heap:  $JAVA_MEM"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Align reads with BWA-MEM2
# ---------------------------------------------------------------------------
# The -R flag sets the read group, which is REQUIRED for GATK downstream.
# Without read groups, MarkDuplicates and HaplotypeCaller will fail.
echo "[Step 1/8] Aligning reads with BWA-MEM2..."
bwa-mem2 mem \
    -t "$THREADS" \
    -R "@RG\tID:${SAMPLE_ID}\tSM:${SAMPLE_ID}\tLB:lib1\tPL:ILLUMINA" \
    -K 100000000 \
    -Y \
    "$REFERENCE" \
    "$FASTQ_R1" "$FASTQ_R2" \
    | samtools sort -@ "$THREADS" -o "${OUTPUT_DIR}/${SAMPLE_ID}.sorted.bam" -

# ---------------------------------------------------------------------------
# Step 2: Index the sorted BAM
# ---------------------------------------------------------------------------
echo "[Step 2/8] Indexing sorted BAM..."
samtools index "${OUTPUT_DIR}/${SAMPLE_ID}.sorted.bam"

# ---------------------------------------------------------------------------
# Step 3: Mark duplicates
# ---------------------------------------------------------------------------
# Flags PCR and optical duplicates so they are excluded from variant calling.
echo "[Step 3/8] Marking duplicates..."
gatk --java-options "-Xmx${JAVA_MEM}" MarkDuplicates \
    -I "${OUTPUT_DIR}/${SAMPLE_ID}.sorted.bam" \
    -O "${OUTPUT_DIR}/${SAMPLE_ID}.dedup.bam" \
    -M "${OUTPUT_DIR}/${SAMPLE_ID}.dedup_metrics.txt" \
    --CREATE_INDEX true

# ---------------------------------------------------------------------------
# Step 4: Base Quality Score Recalibration (BQSR)
# ---------------------------------------------------------------------------
# Corrects systematic errors in base quality scores using known variant sites.
echo "[Step 4/8] Running BaseRecalibrator..."
gatk --java-options "-Xmx${JAVA_MEM}" BaseRecalibrator \
    -I "${OUTPUT_DIR}/${SAMPLE_ID}.dedup.bam" \
    -R "$REFERENCE" \
    --known-sites "$KNOWN_SITES" \
    -O "${OUTPUT_DIR}/${SAMPLE_ID}.recal_data.table"

echo "[Step 4/8] Applying BQSR..."
gatk --java-options "-Xmx${JAVA_MEM}" ApplyBQSR \
    -I "${OUTPUT_DIR}/${SAMPLE_ID}.dedup.bam" \
    -R "$REFERENCE" \
    --bqsr-recal-file "${OUTPUT_DIR}/${SAMPLE_ID}.recal_data.table" \
    -O "${OUTPUT_DIR}/${SAMPLE_ID}.recal.bam"

# ---------------------------------------------------------------------------
# Step 5: Call variants with HaplotypeCaller
# ---------------------------------------------------------------------------
# Using GVCF mode (--emit-ref-confidence GVCF) so the output can be used
# for joint calling later. For single-sample-only analysis, omit this flag.
echo "[Step 5/8] Calling variants with HaplotypeCaller (GVCF mode)..."
gatk --java-options "-Xmx${JAVA_MEM}" HaplotypeCaller \
    -I "${OUTPUT_DIR}/${SAMPLE_ID}.recal.bam" \
    -R "$REFERENCE" \
    -O "${OUTPUT_DIR}/${SAMPLE_ID}.g.vcf.gz" \
    --emit-ref-confidence GVCF \
    -ERC GVCF

# For single-sample genotyping from the GVCF:
echo "[Step 5/8] Genotyping single sample from GVCF..."
gatk --java-options "-Xmx${JAVA_MEM}" GenotypeGVCFs \
    -R "$REFERENCE" \
    -V "${OUTPUT_DIR}/${SAMPLE_ID}.g.vcf.gz" \
    -O "${OUTPUT_DIR}/${SAMPLE_ID}.vcf.gz"

# ---------------------------------------------------------------------------
# Step 6: Normalize variants with bcftools
# ---------------------------------------------------------------------------
# Left-align indels and split multi-allelic sites. This is essential before
# annotation to ensure correct matching against databases.
echo "[Step 6/8] Normalizing variants..."
bcftools norm \
    -m -both \
    -f "$REFERENCE" \
    "${OUTPUT_DIR}/${SAMPLE_ID}.vcf.gz" \
    -Oz -o "${OUTPUT_DIR}/${SAMPLE_ID}.norm.vcf.gz"

tabix -p vcf "${OUTPUT_DIR}/${SAMPLE_ID}.norm.vcf.gz"

# ---------------------------------------------------------------------------
# Step 7: Annotate with VEP
# ---------------------------------------------------------------------------
# Adds consequence predictions, ClinVar significance, gnomAD frequencies,
# REVEL and CADD pathogenicity scores. These annotations are required by
# the filter_by_acmg.py script.
echo "[Step 7/8] Annotating with VEP..."
vep \
    -i "${OUTPUT_DIR}/${SAMPLE_ID}.norm.vcf.gz" \
    --cache --dir_cache "$VEP_CACHE" \
    --assembly GRCh38 --offline \
    --fasta "$REFERENCE" \
    --sift b --polyphen b \
    --symbol --canonical --biotype \
    --vcf \
    -o "${OUTPUT_DIR}/${SAMPLE_ID}.annotated.vcf.gz" \
    --compress_output bgzip

tabix -p vcf "${OUTPUT_DIR}/${SAMPLE_ID}.annotated.vcf.gz"

# ---------------------------------------------------------------------------
# Step 8: Filter for clinically actionable variants
# ---------------------------------------------------------------------------
# Uses the ACMG/AMP filtering script with a default plan. In practice,
# the plan JSON is produced by the genomic-variant-interpretation reasoning
# skill and customized per analysis.
echo "[Step 8/8] Filtering for clinically actionable variants..."

# Create a default plan if none exists
PLAN_FILE="${OUTPUT_DIR}/default_plan.json"
if [[ ! -f "$PLAN_FILE" ]]; then
    cat > "$PLAN_FILE" <<PLAN
{
    "classification_framework": "ACMG/AMP-2015",
    "population_af_threshold": 0.01,
    "computational_thresholds": {
        "REVEL": 0.5,
        "CADD": 20,
        "SpliceAI": 0.5
    },
    "evidence_sources": ["ClinVar", "gnomAD"],
    "inheritance_mode": null,
    "tier_definitions": {
        "Pathogenic": ["PVS1+PS1", "PVS1+PP3", "PS1+PP3"],
        "LikelyPathogenic": ["PVS1", "PS1"],
        "VUS": ["PP3"]
    }
}
PLAN
fi

# Locate the filter script relative to this script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "${SCRIPT_DIR}/filter_by_acmg.py" \
    --vcf "${OUTPUT_DIR}/${SAMPLE_ID}.annotated.vcf.gz" \
    --plan "$PLAN_FILE" \
    --clinvar "${KNOWN_SITES}" \
    --gnomad "${KNOWN_SITES}" \
    --out "${OUTPUT_DIR}/${SAMPLE_ID}.candidates.tsv"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Pipeline Complete ==="
echo "Sorted BAM:       ${OUTPUT_DIR}/${SAMPLE_ID}.sorted.bam"
echo "Deduplicated BAM: ${OUTPUT_DIR}/${SAMPLE_ID}.dedup.bam"
echo "Recalibrated BAM: ${OUTPUT_DIR}/${SAMPLE_ID}.recal.bam"
echo "GVCF:             ${OUTPUT_DIR}/${SAMPLE_ID}.g.vcf.gz"
echo "Genotyped VCF:    ${OUTPUT_DIR}/${SAMPLE_ID}.vcf.gz"
echo "Annotated VCF:    ${OUTPUT_DIR}/${SAMPLE_ID}.annotated.vcf.gz"
echo "Candidates TSV:   ${OUTPUT_DIR}/${SAMPLE_ID}.candidates.tsv"
echo ""
echo "Review candidates.tsv for clinically actionable variants."
echo "For joint calling with additional samples, use the GVCF with"
echo "GenomicsDBImport and GenotypeGVCFs."
