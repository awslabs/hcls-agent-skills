#!/usr/bin/env bash
set -e

image=${1:-hoptimus0-realtime}
region=$(aws configure get region 2>/dev/null || echo "us-east-1")
account=$(aws sts get-caller-identity --query Account --output text)
fullname="${account}.dkr.ecr.${region}.amazonaws.com/${image}:latest"

echo "Building ${fullname}"

# Create ECR repo if it doesn't exist
aws ecr describe-repositories --repository-names "${image}" --region "${region}" > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name "${image}" --region "${region}" > /dev/null

# Login to our ECR
aws ecr get-login-password --region "${region}" | docker login --username AWS --password-stdin "${account}.dkr.ecr.${region}.amazonaws.com"

# Login to DLC ECR to pull base image
aws ecr get-login-password --region "${region}" | docker login --username AWS --password-stdin "763104351884.dkr.ecr.${region}.amazonaws.com"

# Build and push
docker build --platform linux/amd64 -f Dockerfile -t "${image}" . --build-arg REGION="${region}"
docker tag "${image}" "${fullname}"
docker push "${fullname}"

echo "Done: ${fullname}"
