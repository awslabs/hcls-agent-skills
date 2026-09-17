#!/usr/bin/env bash
# setup-s3-bucket.sh
# Creates or validates an S3 bucket for AWS HealthOmics workflows.
# Sets up standard prefix structure for inputs, outputs, and cache.
#
# Usage:
#   ./scripts/setup-s3-bucket.sh \
#       --bucket-name <BUCKET_NAME> \
#       --region <REGION> \
#       [--create-if-missing] \
#       [--enable-versioning]
#
# Prerequisites:
#   - AWS CLI v2 configured with S3 permissions

set -euo pipefail

# --- Defaults ---
BUCKET_NAME=""
REGION=""
CREATE_IF_MISSING=false
ENABLE_VERSIONING=false

# --- Parse Arguments ---
while [[ $# -gt 0 ]]; do
    case $1 in
        --bucket-name) BUCKET_NAME="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --create-if-missing) CREATE_IF_MISSING=true; shift ;;
        --enable-versioning) ENABLE_VERSIONING=true; shift ;;
        -h|--help)
            echo "Usage: $0 --bucket-name NAME --region REGION [--create-if-missing] [--enable-versioning]"
            echo ""
            echo "Options:"
            echo "  --bucket-name        Name of the S3 bucket"
            echo "  --region             AWS region (must be HealthOmics-supported)"
            echo "  --create-if-missing  Create the bucket if it does not exist"
            echo "  --enable-versioning  Enable bucket versioning"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# --- Validate Required Parameters ---
if [[ -z "$BUCKET_NAME" || -z "$REGION" ]]; then
    echo "ERROR: --bucket-name and --region are required."
    echo "Run with --help for usage."
    exit 1
fi

# --- Validate Region ---
SUPPORTED_REGIONS="us-east-1 us-east-2 us-west-2 eu-west-1 eu-west-2 eu-central-1 ap-southeast-1 ap-northeast-1 ap-northeast-2 il-central-1"
if ! echo "$SUPPORTED_REGIONS" | grep -qw "$REGION"; then
    echo "WARNING: Region '$REGION' may not support HealthOmics."
    echo "Supported regions: $SUPPORTED_REGIONS"
    echo ""
fi

# --- Check if Bucket Exists ---
echo "Checking if bucket '$BUCKET_NAME' exists..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" --region "$REGION" 2>/dev/null; then
    echo "[OK] Bucket '$BUCKET_NAME' exists."

    # Verify region
    BUCKET_REGION=$(aws s3api get-bucket-location --bucket "$BUCKET_NAME" --query 'LocationConstraint' --output text 2>/dev/null || echo "")
    # us-east-1 returns "None" or null for location constraint
    if [[ "$BUCKET_REGION" == "None" || -z "$BUCKET_REGION" ]]; then
        BUCKET_REGION="us-east-1"
    fi

    if [[ "$BUCKET_REGION" != "$REGION" ]]; then
        echo "WARNING: Bucket is in region '$BUCKET_REGION' but you specified '$REGION'."
        echo "HealthOmics requires the bucket to be in the same region as the workflow."
    fi

elif [[ "$CREATE_IF_MISSING" == "true" ]]; then
    echo "Bucket not found. Creating..."

    if [[ "$REGION" == "us-east-1" ]]; then
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$REGION"
    else
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$REGION" \
            --create-bucket-configuration LocationConstraint="$REGION"
    fi
    echo "[OK] Bucket created: s3://${BUCKET_NAME}"

    # Block public access
    echo "Blocking public access..."
    aws s3api put-public-access-block \
        --bucket "$BUCKET_NAME" \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
        --region "$REGION"
    echo "[OK] Public access blocked."
else
    echo "ERROR: Bucket '$BUCKET_NAME' does not exist. Use --create-if-missing to create it."
    exit 1
fi

# --- Enable Versioning (optional) ---
if [[ "$ENABLE_VERSIONING" == "true" ]]; then
    echo "Enabling versioning..."
    aws s3api put-bucket-versioning \
        --bucket "$BUCKET_NAME" \
        --versioning-configuration Status=Enabled \
        --region "$REGION"
    echo "[OK] Versioning enabled."
fi

# --- Create Standard Prefix Structure ---
echo ""
echo "Creating standard directory structure..."

# Create zero-byte marker objects to establish prefixes
PREFIXES=("inputs/" "outputs/" "workflows/" "references/" "cache/")
for prefix in "${PREFIXES[@]}"; do
    if ! aws s3api head-object --bucket "$BUCKET_NAME" --key "$prefix" --region "$REGION" 2>/dev/null; then
        aws s3api put-object \
            --bucket "$BUCKET_NAME" \
            --key "$prefix" \
            --content-length 0 \
            --region "$REGION" >/dev/null
        echo "  Created: s3://${BUCKET_NAME}/${prefix}"
    else
        echo "  Exists:  s3://${BUCKET_NAME}/${prefix}"
    fi
done

echo ""
echo "=== SUMMARY ==="
echo "Bucket: s3://${BUCKET_NAME}"
echo "Region: $REGION"
echo ""
echo "Directory structure:"
echo "  s3://${BUCKET_NAME}/inputs/      - Upload input files here (FASTQ, BAM, VCF)"
echo "  s3://${BUCKET_NAME}/outputs/     - HealthOmics writes run results here"
echo "  s3://${BUCKET_NAME}/workflows/   - Workflow ZIP packages stored here"
echo "  s3://${BUCKET_NAME}/references/  - Reference genomes and indices"
echo "  s3://${BUCKET_NAME}/cache/       - Call caching location (optional)"
echo ""
echo "Use these in your .healthomics/config.toml:"
echo "  run_output_uri = \"s3://${BUCKET_NAME}/outputs/\""
echo "  cache_s3_location = \"s3://${BUCKET_NAME}/cache/\""
