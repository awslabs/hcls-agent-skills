---
name: bioinformatics-on-healthomics
description: >
  Guides users through bioinformatics analysis on AWS HealthOmics. Covers analysis
  type selection (alignment, variant calling, QC, interpretation), workflow generation
  in Nextflow or WDL, container sourcing from public registries, infrastructure setup
  (S3, ECR, IAM), workflow registration, parameter preparation, execution, and
  monitoring. Use when a user wants to run any bioinformatics pipeline on HealthOmics,
  set up genomics infrastructure on AWS, create a new analysis workflow, or run
  existing tools like BWA, GATK, DeepVariant, FastQC, or similar on HealthOmics.
  Triggers include "HealthOmics", "bioinformatics", "genomics pipeline", "Nextflow",
  "WDL", "BWA", "GATK", "DeepVariant", "FastQC", "variant calling", "alignment",
  "RNA-seq", "whole genome sequencing", "ECR pull-through", "workflow registration",
  "run cache"
usage: Invoke when a user wants to build, deploy, or run a bioinformatics workflow on AWS HealthOmics.
version: 1.0.0
tags:
  - skill
  - category:pipeline
  - genomics
  - bioinformatics
  - healthomics
  - hcls
validated_against:
  date: 2025-07-01
  packages: {healthomics-mcp: "latest", aws-cli: "2.x"}
---

# Bioinformatics Analysis on AWS HealthOmics

End-to-end skill for creating, deploying, and running bioinformatics workflows on AWS
HealthOmics. Designed for users who may not be deeply technical — the agent guides
through every decision with clear explanations.

---

## Response Structure

When guiding a user through a HealthOmics bioinformatics workflow, follow this order:

1. **Clarify the analysis goal** — confirm analysis type, organism, data format
2. **Recommend tools** — suggest a pipeline with rationale; ask for confirmation
3. **Choose workflow language** — WDL or Nextflow based on complexity
4. **Set up infrastructure** — containers (ECR pull-through), S3, IAM, run cache
5. **Generate workflow code** — lint before registration
6. **Register and run** — deploy, start run, monitor progress
7. **Handle failures** — diagnose with MCP tools, iterate with caching
8. **Deliver results** — point to outputs, suggest optimization

---

## Mental Model

AWS HealthOmics is a fully managed service that runs genomics workflows. You provide:
1. A workflow definition (Nextflow or WDL)
2. Container images in ECR (pulled from public registries via pull-through cache)
3. Input data in S3
4. An IAM service role

HealthOmics handles compute provisioning, scheduling, and output collection.

### Key Constraints
- All containers must be in private ECR (use pull-through cache for public images)
- All input/output data must be in S3, same region as the workflow
- A service role with trust policy for `omics.amazonaws.com` is required
- Supported regions: us-east-1, us-east-2, us-west-2, eu-west-1, eu-west-2,
  eu-central-1, ap-southeast-1, ap-northeast-1, ap-northeast-2, il-central-1

---

## Prerequisites

Before starting, verify:
1. **AWS credentials** configured for a HealthOmics-supported region
2. **AWS CLI v2** installed
3. **HealthOmics MCP server** available and enabled (use `aws-healthomics` power)
4. **RODA MCP** available for test data discovery (optional but recommended)

---

## Phase 1: Understanding the User's Analysis

Ask the user what they want to accomplish. Common analysis types:

| Analysis Type | Common Tools | Input | Output |
|---|---|---|---|
| Quality Control | FastQC, MultiQC, fastp | FASTQ | QC reports, trimmed FASTQ |
| Alignment | BWA-MEM2, STAR, minimap2, bowtie2 | FASTQ + Reference | BAM/CRAM |
| Variant Calling | GATK HaplotypeCaller, DeepVariant, Strelka2, FreeBayes | BAM + Reference | VCF/gVCF |
| Structural Variants | Manta, DELLY, LUMPY, Sniffles | BAM + Reference | VCF |
| RNA-Seq | STAR + featureCounts, Salmon, kallisto | FASTQ + Reference/Index | Counts matrix |
| Methylation | Bismark, bwa-meth | FASTQ + Reference | Methylation calls |
| Variant Annotation | VEP, SnpEff, ANNOVAR | VCF + Databases | Annotated VCF |
| Joint Genotyping | GATK GenomicsDBImport + GenotypeGVCFs | gVCFs | Joint VCF |
| Somatic Calling | Mutect2, VarScan2, Strelka2-somatic | Tumor/Normal BAMs | Somatic VCF |

### Recommendations Engine

Based on the user's stated goal, recommend a pipeline of tools. Example combinations:

**Whole Genome Sequencing (germline):**
1. fastp (QC + trimming) → BWA-MEM2 (alignment) → GATK MarkDuplicates → GATK HaplotypeCaller → VCF filtering

**RNA-Seq differential expression:**
1. fastp (QC) → STAR (alignment) → featureCounts (quantification)

**Targeted panel / Exome:**
1. fastp → BWA-MEM2 → GATK MarkDuplicates → GATK HaplotypeCaller (with intervals) → VQSR or hard filtering

Always explain WHY each tool is recommended and ask for confirmation before proceeding.

---

## Phase 2: Workflow Language Selection

Ask the user's preference:
- **WDL** (recommended for most users) — clearer syntax, explicit inputs/outputs, better for linear pipelines
- **Nextflow** — better for complex data-driven pipelines with many branch points

If the user has no preference, default to **WDL 1.1** for simpler pipelines and
**Nextflow DSL2** for complex multi-sample scatter-gather patterns.

---

## Phase 3: Container Image Sourcing

For each tool in the pipeline, find container images in this priority order:

1. **quay.io/biocontainers/** — preferred, curated bioinformatics containers
2. **public.ecr.aws/** — AWS-hosted public images
3. **Docker Hub** (registry-1.docker.io) — broad availability but rate limits apply

### Search Strategy

For each tool, search for the latest stable image:
- quay.io: `quay.io/biocontainers/<tool>:<version>--<hash>`
- ECR Public: `public.ecr.aws/biocontainers/<tool>:<version>`
- Docker Hub: `broadinstitute/gatk:<version>`, `staphb/<tool>:<version>`

### Setting Up ECR Pull-Through Cache

HealthOmics requires containers in private ECR. Use pull-through cache to automatically
mirror public images.

Use the HealthOmics MCP `CreatePullThroughCacheForHealthOmics` tool:
- Specify `upstream_registry` as `docker-hub`, `quay`, or `ecr-public`
- Optionally set `ecr_repository_prefix`
- For `quay` and `ecr-public`: no credentials needed
- For `docker-hub`: a `credential_arn` is **required** (see below)
- The tool automatically creates the cache rule, updates registry permissions for HealthOmics,
  and creates repository creation templates with correct permissions

### Docker Hub Authentication (Required for docker-hub pull-through cache)

Docker Hub rate-limits anonymous pulls. To use Docker Hub with pull-through cache,
store credentials in Secrets Manager and pass the ARN as `credential_arn`:

1. Create a KMS key: `aws kms create-key` → save the ARN
2. Store credentials: `aws secretsmanager create-secret --kms-key-id <KEY> --secret-string '{"username":"...","password":"..."}'` → save the secret ARN
3. Pass `credential_arn` to `CreatePullThroughCacheForHealthOmics`

If the user has no Docker Hub account, prefer `quay.io/biocontainers` (no auth needed).

To verify the setup, use `ValidateHealthOmicsECRConfig` which checks all pull-through
cache rules, registry permissions, and repository templates.

To list existing rules and their HealthOmics usability, use `ListPullThroughCacheRules`.

### Verify Container Availability

Use the HealthOmics MCP `CheckContainerAvailability` tool with `initiate_pull_through: true`
to confirm each container is accessible. This verifies the image exists, checks HealthOmics
access permissions, and can trigger the initial pull-through.

To copy a specific image from an upstream registry to private ECR with HealthOmics
permissions, use `CloneContainerToECR` with the source image reference (supports
Docker Hub shorthand, quay.io, and public.ecr.aws formats).

### Container Registry Map

For workflows referencing public registry URIs, create a container registry map so
HealthOmics redirects pulls to your private ECR.

Use the HealthOmics MCP `CreateContainerRegistryMap` tool:
- Set `include_pull_through_caches: true` to auto-discover HealthOmics-usable caches
- Optionally provide `additional_registry_mappings` or `image_mappings` for overrides
- The output can be passed directly to `CreateAHOWorkflow` via the `container_registry_map`
  parameter, or saved to S3 and referenced via `container_registry_map_uri`

---

## Phase 4: Workflow Generation

Generate the workflow definition based on the chosen tools and language. Use steering documentation best practices in healthomics power

### WDL Structure
```
workflow/
  main.wdl          # Top-level workflow
  tasks/
    fastqc.wdl      # Individual task definitions
    bwa_mem2.wdl
    gatk_hc.wdl
  structs/
    sample.wdl      # Struct definitions
  parameters.json   # Example parameters
  README.md         # Documentation
```

### Nextflow Structure
```
workflow/
  main.nf           # Entry point
  nextflow.config   # Configuration
  modules/
    fastqc.nf       # Process definitions
    bwa_mem2.nf
    gatk_hc.nf
  conf/
    healthomics.config  # HealthOmics-specific config
  nextflow_schema.json  # Input schema (nf-schema)
  parameters.json       # Example parameters
  README.md             # Documentation
```

### Key Rules for HealthOmics Compatibility

1. Every task/process MUST declare CPU, memory, and container
2. Use at least 2 CPUs and 4 GB memory per task
3. All final outputs must be declared at workflow level
4. For Nextflow: publishDir must use `/mnt/workflow/pubdir` as base
5. For WDL: use `~{var}` interpolation and `<<< >>>` command delimiters
6. Use `set -eu` in all command blocks

### Lint Before Deploy

For WDL/CWL workflows, use the HealthOmics MCP `LintAHOWorkflowDefinition` or
`LintAHOWorkflowBundle` tool to validate before deployment.

---

## Phase 5: Infrastructure Setup (First-Time Only)

On first use, set up the required AWS infrastructure. Ask the user for each component
or offer to create it.

### 5A: S3 Bucket

Create an S3 bucket for workflow inputs, outputs, and optional call caching:

```bash
aws s3 mb s3://<BUCKET_NAME> --region <REGION>
```

The bucket is used for:
- **Input files** (FASTQ, BAM, VCF, references)
- **Workflow outputs** (results written by HealthOmics)
- **Call caching** (optional, for resuming interrupted runs)

### 5B: IAM Service Role

Create a service role for HealthOmics:

```bash
# Create the role with HealthOmics trust policy
aws iam create-role \
    --role-name <ROLE_NAME> \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "omics.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }'
```

The role needs:
- Trust policy for `omics.amazonaws.com`
- S3: `s3:GetObject`, `s3:PutObject`, `s3:ListBucket`, `s3:GetBucketLocation` on the bucket
- ECR: `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, `ecr:BatchCheckLayerAvailability`
- Logs: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` on `/aws/omics/*`

### 5C: Run Cache Setup

Ask the user about call caching. Explain that call caching allows HealthOmics to skip
re-running tasks whose inputs haven't changed — this is especially valuable during
iterative workflow development where some steps (like alignment) succeed but later
steps (like variant calling) need tuning.

**Ask the user which cache behavior they prefer:**

- **CACHE_ON_FAILURE** (recommended for development) — Caches results from successful
  tasks when a run fails. On the next run, tasks with identical inputs are skipped.
  Ideal for iterative development: fix a failing step, re-run, and only the changed/failed
  tasks execute again. Upstream steps that already succeeded are served from cache.

- **CACHE_ALWAYS** — Caches results from every run regardless of outcome. Useful for
  production pipelines where you re-run the same workflow on new samples and want to
  skip any tasks that happen to have identical inputs (e.g., reference indexing).

Create the run cache using `CreateAHORunCache`:
- `cache_behavior` — the user's choice above
- `cache_s3_location` — an S3 prefix for cache storage (e.g., `s3://<BUCKET>/healthomics-cache/`)
- `name` — descriptive name (e.g., "dev-cache" or "production-cache")

Save the returned `cache_id` for use in runs.

### 5D: Configuration File

Save settings to `.healthomics/config.toml`:

```toml
omics_iam_role = "arn:aws:iam::<ACCOUNT_ID>:role/<ROLE_NAME>"
run_output_uri = "s3://<BUCKET>/healthomics-outputs/"
run_storage_type = "DYNAMIC"
cache_id = "<CACHE_ID>"
cache_behavior = "CACHE_ON_FAILURE"  # or "CACHE_ALWAYS"
cache_s3_location = "s3://<BUCKET>/healthomics-cache/"
aws_region = "<REGION>"
```

---

## Phase 6: Workflow Registration

Package and deploy the workflow to HealthOmics using the MCP tools:

1. **Package the workflow** — Use `PackageAHOWorkflow`:
   - Set `main_file_content` to the path of your main workflow file (e.g., `./workflow/main.wdl`)
   - Set `main_file_name` appropriately (e.g., `main.wdl` or `main.nf`)
   - Provide any imports or modules via `additional_files` (dict of filename → file path)

2. **Register the workflow** — Use `CreateAHOWorkflow`:
   - Set `name` for the workflow
   - Set `definition_source` to the local ZIP path or pass the base64 output from PackageAHOWorkflow
   - Set `engine` to `WDL`, `NEXTFLOW`, or `CWL`
   - Optionally provide `container_registry_map` or `container_registry_map_uri`
   - Optionally provide `description` and `storage_type` (default DYNAMIC)

3. **Verify registration** — Use `GetAHOWorkflow` to confirm status is ACTIVE

Example flow:
```
PackageAHOWorkflow(main_file_content="./workflow/main.nf", additional_files={"modules/bwa.nf": "./workflow/modules/bwa.nf", ...})
  → CreateAHOWorkflow(name="my-pipeline", definition_source=<zip_path>, engine="NEXTFLOW")
  → GetAHOWorkflow(workflow_id=<id>)  # verify ACTIVE
```

---

## Phase 7: Preparing Input Parameters

Help the user identify input files.

### Finding Files in S3
Use the HealthOmics MCP `SearchGenomicsFiles` tool to find FASTQ, BAM, VCF, or
reference files in configured S3 buckets.

### Using Test Data from RODA
If the RODA MCP is available, use it to find public datasets for testing:
- Search for relevant datasets (e.g., "1000 genomes", "giab", "clinvar")
- Preview dataset structure
- Identify appropriate test files

Common test datasets:
- **GIAB (Genome in a Bottle)** — truth sets for variant calling validation
- **1000 Genomes** — population-scale WGS data
- **ClinVar** — clinically relevant variant annotations
- **ENCODE** — functional genomics data

### Building parameters.json

Create a parameters file matching the workflow's parameter template:
```json
{
  "input_fastq_r1": "s3://bucket/data/sample_R1.fastq.gz",
  "input_fastq_r2": "s3://bucket/data/sample_R2.fastq.gz",
  "reference_fasta": "s3://bucket/references/GRCh38.fasta",
  "sample_name": "NA12878",
  "output_prefix": "results"
}
```

---

## Phase 8: Running the Workflow

### Start a Run

Use the HealthOmics MCP `StartAHORun` tool:
- `workflow_id` — from the registration step
- `role_arn` — from `.healthomics/config.toml` (`omics_iam_role`)
- `name` — descriptive name for the run
- `output_uri` — from `.healthomics/config.toml` (`run_output_uri`)
- `parameters` — the workflow parameters (from parameters.json)
- `storage_type` — from config (default DYNAMIC)
- `cache_id` — resolved automatically (see below)
- `cache_behavior` — from `.healthomics/config.toml` (CACHE_ON_FAILURE or CACHE_ALWAYS)

### Resolving the Run Cache

The user should never need to remember or specify a cache ID. Resolve it automatically:

1. **Check `.healthomics/config.toml`** — if `cache_id` is set, use it directly.
2. **Check session history** — if a cache was created earlier in this session, use that cache ID.
3. **If neither is available**, call `ListAHORunCaches` to find existing caches:
   - If exactly **one** cache exists → use it automatically.
   - If **multiple** caches exist → present the list to the user (showing name, behavior,
     and creation date) and ask them to pick one.
   - If **no** caches exist → prompt the user to create one (see Phase 5C).
4. Once resolved, **save the `cache_id` to `.healthomics/config.toml`** so future runs
   use it without asking again.

**Always pass `cache_id` and `cache_behavior` when a run cache is available.** During
iterative development this prevents re-running expensive tasks (like alignment or
duplicate marking) that already succeeded on a previous run.

### Monitor the Run

Use the HealthOmics MCP tools for monitoring:
- `GetAHORun` — check overall status, timing, and failure reasons
- `ListAHORunTasks` — see individual task progress and status
- `GetAHORunLogs` — view high-level workflow execution events
- `GetAHORunEngineLogs` — view engine stdout/stderr for debugging
- `GetAHOTaskLogs` — view logs for a specific task
- `GetAHORunManifestLogs` — view workflow summary with resource metrics

### Handle Failures

If a run fails:
1. Use `DiagnoseAHORunFailure` to get comprehensive diagnostics including:
   - Failure reasons
   - Engine logs
   - Failed task logs
   - Actionable recommendations
2. Common issues:
   - **S3 object not found** — verify input paths exist
   - **Container pull failed** — check ECR permissions and pull-through cache
   - **Out of memory** — increase task memory in workflow definition
   - **Timeout** — increase task timeout or check for infinite loops
3. Fix the workflow and create a new version via `CreateAHOWorkflowVersion`
4. Re-run with the new version

---

## Phase 9: Results and Next Steps

After successful completion:
- Outputs are in the S3 output location
- Use `GetAHORun` to find the exact `runOutputUri`
- For performance optimization, use `AnalyzeAHORunPerformance`
- For visualization, use `GenerateAHORunTimeline`

---

## Failure Playbook

| Symptom | Fix |
|---|---|
| "HealthOmics is not available" | Use a supported region |
| Container pull failed | Use `CreatePullThroughCacheForHealthOmics` to fix PTC rules |
| Access denied on S3 | Update IAM role policy with correct bucket ARN |
| Workflow stuck in CREATING | Wait up to 10 min; large workflows take time |
| Registry map mismatch | Re-register workflow after map update |
| Parameter validation error | Check workflow parameter template for name/type mismatches |

---

## Critical Rules

1. **Always use HealthOmics MCP tools** — never raw AWS CLI for HealthOmics calls.
2. **Container priority**: quay.io/biocontainers → public.ecr.aws → Docker Hub.
3. **Pull-through cache is mandatory** — use `CreatePullThroughCacheForHealthOmics`.
4. **Region consistency**: S3, ECR, and HealthOmics must share the same region.
5. **Lint before deploy**: Validate WDL/CWL with `LintAHOWorkflowDefinition` before registration.
6. **Config file**: Read `.healthomics/config.toml` for saved preferences.
7. **Test data**: Check RODA MCP for public datasets before asking users to upload.
8. **Explain every step** and confirm before destructive actions.
9. **Default to DYNAMIC storage** for cost efficiency.
10. **Diagnostics**: `DiagnoseAHORunFailure` for failures, `AnalyzeAHORunPerformance` for optimization.
11. **Call caching**: Default to CACHE_ON_FAILURE for dev. Resolve cache ID from config automatically — only prompt when multiple caches exist.
