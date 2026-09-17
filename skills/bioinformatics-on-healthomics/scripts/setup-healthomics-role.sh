#!/usr/bin/env bash
# setup-healthomics-role.sh
# Creates or validates an IAM service role for AWS HealthOmics.
# The role grants HealthOmics permissions to access S3, ECR, and CloudWatch Logs.
#
# Usage:
#   ./scripts/setup-healthomics-role.sh \
#       --role-name <ROLE_NAME> \
#       --region <REGION> \
#       --s3-bucket <BUCKET_NAME> \
#       [--create-if-missing] \
#       [--ecr-prefix "docker-hub,quay,ecr-public"]
#
# Prerequisites:
#   - AWS CLI v2 configured with IAM permissions to create roles and policies
#   - jq installed

set -euo pipefail

# --- Defaults ---
ROLE_NAME=""
REGION=""
S3_BUCKET=""
CREATE_IF_MISSING=false
ECR_PREFIXES="docker-hub,quay,ecr-public"

# --- Parse Arguments ---
while [[ $# -gt 0 ]]; do
    case $1 in
        --role-name) ROLE_NAME="$2"; shift 2 ;;
        --region) REGION="$2"; shift 2 ;;
        --s3-bucket) S3_BUCKET="$2"; shift 2 ;;
        --create-if-missing) CREATE_IF_MISSING=true; shift ;;
        --ecr-prefix) ECR_PREFIXES="$2"; shift 2 ;;
        -h|--help)
            echo "Usage: $0 --role-name NAME --region REGION --s3-bucket BUCKET [--create-if-missing] [--ecr-prefix PREFIX1,PREFIX2]"
            echo ""
            echo "Options:"
            echo "  --role-name          Name for the IAM role"
            echo "  --region             AWS region"
            echo "  --s3-bucket          S3 bucket name for inputs/outputs"
            echo "  --create-if-missing  Create the role if it does not exist"
            echo "  --ecr-prefix         Comma-separated ECR repository prefixes (default: docker-hub,quay,ecr-public)"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# --- Validate Required Parameters ---
if [[ -z "$ROLE_NAME" || -z "$REGION" || -z "$S3_BUCKET" ]]; then
    echo "ERROR: --role-name, --region, and --s3-bucket are required."
    echo "Run with --help for usage."
    exit 1
fi

# --- Get Account ID ---
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text --region "$REGION")
echo "Account: $ACCOUNT_ID | Region: $REGION"

# --- Trust Policy ---
TRUST_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "omics.amazonaws.com"
            },
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "$ACCOUNT_ID"
                }
            }
        }
    ]
}
EOF
)

# --- Build ECR Resource ARNs ---
IFS=',' read -ra PREFIXES <<< "$ECR_PREFIXES"
ECR_RESOURCES=""
for prefix in "${PREFIXES[@]}"; do
    prefix=$(echo "$prefix" | xargs)  # trim whitespace
    ECR_RESOURCES="${ECR_RESOURCES}\"arn:aws:ecr:${REGION}:${ACCOUNT_ID}:repository/${prefix}/*\","
done
# Remove trailing comma
ECR_RESOURCES="${ECR_RESOURCES%,}"

# --- Inline Policy ---
POLICY_DOCUMENT=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "S3Access",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:AbortMultipartUpload",
                "s3:ListMultipartUploadParts",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::${S3_BUCKET}",
                "arn:aws:s3:::${S3_BUCKET}/*"
            ]
        },
        {
            "Sid": "ECRAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchCheckLayerAvailability"
            ],
            "Resource": [
                ${ECR_RESOURCES}
            ]
        },
        {
            "Sid": "ECRAuth",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogStreams"
            ],
            "Resource": [
                "arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:/aws/omics/*"
            ]
        }
    ]
}
EOF
)

# --- Check if Role Exists ---
echo ""
echo "Checking if role '$ROLE_NAME' exists..."
if aws iam get-role --role-name "$ROLE_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "[OK] Role '$ROLE_NAME' already exists."
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text --region "$REGION")
    echo "     ARN: $ROLE_ARN"

    # Update trust policy to ensure it's correct
    echo "Updating trust policy..."
    aws iam update-assume-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-document "$TRUST_POLICY" \
        --region "$REGION"
    echo "[OK] Trust policy updated."

    # Update inline policy
    echo "Updating inline policy..."
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "HealthOmicsServicePolicy" \
        --policy-document "$POLICY_DOCUMENT" \
        --region "$REGION"
    echo "[OK] Inline policy updated."

elif [[ "$CREATE_IF_MISSING" == "true" ]]; then
    echo "Role not found. Creating..."
    ROLE_ARN=$(aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY" \
        --description "Service role for AWS HealthOmics workflow runs" \
        --query 'Role.Arn' \
        --output text \
        --region "$REGION")
    echo "[OK] Role created: $ROLE_ARN"

    # Attach inline policy
    echo "Attaching inline policy..."
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "HealthOmicsServicePolicy" \
        --policy-document "$POLICY_DOCUMENT" \
        --region "$REGION"
    echo "[OK] Policy attached."

    # Wait for role propagation
    echo "Waiting for IAM propagation (10 seconds)..."
    sleep 10
    echo "[OK] Role ready."
else
    echo "ERROR: Role '$ROLE_NAME' does not exist. Use --create-if-missing to create it."
    exit 1
fi

echo ""
echo "=== SUMMARY ==="
echo "Role Name: $ROLE_NAME"
echo "Role ARN:  arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo "S3 Bucket: $S3_BUCKET"
echo "ECR Prefixes: $ECR_PREFIXES"
echo "Region:    $REGION"
echo ""
echo "The role has permissions for:"
echo "  - S3 read/write on s3://${S3_BUCKET}/*"
echo "  - ECR image pull from prefixes: ${ECR_PREFIXES}"
echo "  - CloudWatch Logs write to /aws/omics/*"
echo ""
echo "Use this ARN in your .healthomics/config.toml:"
echo "  omics_iam_role = \"arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}\""
