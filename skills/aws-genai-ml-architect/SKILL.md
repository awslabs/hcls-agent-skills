---
name: aws-genai-ml-architect
description: Reasoning skill for designing AWS GenAI and ML architectures for healthcare and life sciences workloads. Use when the user asks to choose between SageMaker and Bedrock, design a RAG system over medical literature, architect clinical NLP or medical imaging inference, plan genomics or drug discovery pipelines on AWS, address HIPAA/PHI compliance in ML systems, design MLOps for regulated clinical models, or optimize cost for HCLS ML workloads. Triggers include "AWS architecture", "SageMaker vs Bedrock", "HIPAA ML", "clinical RAG", "medical imaging inference", "genomics on AWS", "PHI training", "MLOps healthcare", "Bedrock guardrails", "HealthLake", "HCLS cloud architecture", "BAA compliance", "SageMaker endpoint", "Bedrock knowledge base", "clinical NLP on AWS", "FDA SaMD on AWS".
usage: Invoke when designing AWS GenAI/ML architectures for HCLS workloads, choosing between SageMaker and Bedrock, or addressing HIPAA compliance.
version: 1.0.0
tags: [skill, category:reasoning, aws, sagemaker, bedrock, architecture, hcls, genai]
---

# AWS GenAI/ML Architect (HCLS)

## Overview

This skill teaches the agent how to reason about AWS GenAI and ML architecture
decisions for healthcare and life sciences (HCLS) workloads. It does not
prescribe CLI commands or IaC templates — it encodes the decision frameworks
an experienced HCLS cloud architect uses to pick services, enforce compliance,
and avoid common pitfalls. Pair this skill with a pipeline skill when concrete IaC or deployment artifacts are needed.

HCLS workloads are distinguished from generic ML workloads by three constraints
that dominate every decision: PHI handling under HIPAA, high cost of
hallucination in clinical outputs, and distribution shift driven by coding
changes, site onboarding, and seasonal care patterns. Keep these in mind at
every step.

## Usage

Invoke this skill when the user asks architecture-level questions such as:

- "Should I use Bedrock or SageMaker for summarizing clinical notes?"
- "How do I build RAG over medical literature on AWS?"
- "What's the right inference pattern for whole-slide images?"
- "How do I train a model on PHI safely?"
- "What should my MLOps stack look like for a clinical risk model?"

Work through the decisions in this order:

1. Clarify the clinical / scientific use case and PHI exposure.
2. Apply the service selection framework.
3. Overlay HCLS architecture patterns for the specific modality.
4. Enforce security and compliance decision points.
5. Add MLOps, monitoring, and cost considerations.
6. Surface common mistakes before finalizing.

State assumptions explicitly when the user has not specified payload size,
latency SLO, PHI status, or regulatory posture.

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail
The decision trees and frameworks in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Present only the final recommendation with supporting evidence.


## Core Concepts

- **PHI vs. de-identified data**: PHI requires HIPAA-eligible services, a
  signed BAA, and stricter isolation. De-identified or synthetic data relaxes
  some controls but downstream re-identification risk should still be assessed.
- **Foundation model (FM) vs. custom model**: FMs are general, fast to ship,
  and priced per token/call. Custom models are domain-specific, require
  training data and ops, and are priced per compute hour.
- **Sync vs. async vs. batch inference**: Latency SLO, payload size, and
  traffic shape determine the right endpoint type, not model size alone.
- **Grounding vs. generation**: Clinical outputs must be grounded in
  retrievable sources (RAG, structured lookups) whenever a wrong answer can
  harm patients or invite regulatory risk.
- **Distribution shift is the default, not the exception**: Healthcare data
  shifts with every ICD coding update, new site, season, and care pathway
  change. Design for it from day one.

## Service Selection Framework

Use this as the first-cut decision:

- **Bedrock** when:
  - Using a foundation model as-is (summarization, extraction, Q&A over text)
  - Building RAG with Knowledge Bases or Agents
  - You want managed guardrails for PII/PHI redaction and toxicity
  - You do not want to manage training, endpoints, or GPU capacity

- **SageMaker** when:
  - Custom training or fine-tuning on proprietary clinical or -omics data
  - Specialized models (medical imaging CNNs, custom NER, survival models)
  - You need full control over container, network, and instance type
  - Building MLOps pipelines with model registry and approval workflows

- **Both** when:
  - FM handles unstructured text while a custom model scores structured risk
  - An ensemble combines an FM summary with a specialized classifier
  - RAG retrieval uses a custom embedding model trained on clinical text

Rule of thumb: start with Bedrock for any text-centric use case. Move to
SageMaker only when FM accuracy, cost, latency, or data residency forces it.

## HCLS Architecture Patterns

Match the modality to the pattern:

- **Clinical note summarization / abstraction**: Bedrock with a small,
  instruction-tuned FM, prompt templates reviewed by clinicians, and
  Bedrock Guardrails configured for PHI redaction and denied topics.
  Always require source-span citations back into the note.

- **Medical literature / guideline RAG**: Bedrock Knowledge Bases backed by
  OpenSearch Serverless. Chunk by semantic section (abstract, methods,
  results, guideline recommendation) rather than fixed token windows —
  clinicians reason at section granularity, and fixed chunks split tables
  and dosing guidance. Store source metadata (PMID, guideline version,
  publication date) for traceability.

- **Pathology and radiology inference**: SageMaker async endpoints for
  whole-slide images and DICOM volumes. Payloads exceed real-time endpoint
  limits and inference times exceed sync SLOs. Pre-process (tiling,
  resampling) in SageMaker Processing jobs before invoking the endpoint.

- **Genomics pipelines**: SageMaker Processing jobs orchestrated by Step
  Functions for custom workflows; HealthOmics when the workflow fits its
  managed WDL/Nextflow execution model. Use HealthOmics variant and
  annotation stores for queryable genomic data.

- **Drug discovery and molecular modeling**: SageMaker HyperPod for
  distributed training of large structural or property-prediction models.
  Bedrock for molecular description, literature mining, and chemistry Q&A;
  never for final property prediction where accuracy is load-bearing.

- **Ambient clinical documentation**: Bedrock for transcription
  post-processing and structured note generation; guardrails plus
  human-in-the-loop sign-off in the EHR.

## Data Architecture

Pick the store by data shape and access pattern:

- **FHIR clinical data** → HealthLake. Supports FHIR-native queries and
  integrated NLP. Export to S3 for ML training.
- **Observational / claims research** → OMOP CDM on Redshift or Athena.
  Standard vocabulary enables reuse of published phenotype definitions.
- **Genomics** → S3 as the source of truth for VCF, BAM, CRAM, FASTQ;
  Lake Formation for governance; Athena for ad-hoc queries; HealthOmics
  stores for indexed access.
- **Medical imaging** → S3 for raw DICOM; HealthImaging for indexed,
  sub-image access and integration with inference pipelines.
- **Unstructured documents** (PDFs, scanned notes) → S3 + Textract for
  extraction, then route structured output to the appropriate store above.

Cross-cutting: Lake Formation for fine-grained access control across
analyst personas; Glue Data Catalog as the single metadata plane.

## Security & Compliance

Treat compliance as a set of hard gates, not a checklist at the end.

- **HIPAA BAA**: Only use services on the AWS HIPAA-eligible list for any
  workflow touching PHI. Verify eligibility for every service in the
  architecture, including logging and monitoring sinks.
- **Network isolation**: PHI workloads run in private subnets with no
  internet egress. Use VPC endpoints for S3, SageMaker, Bedrock, KMS, and
  CloudWatch. Enable SageMaker network isolation on training jobs and
  endpoints handling PHI.
- **Encryption**: Customer-managed KMS keys for S3, EBS, SageMaker
  volumes, and Bedrock Knowledge Base vector stores. TLS 1.2 or higher in
  transit. Scope key policies so only the intended roles can decrypt.
- **Audit and detection**: CloudTrail (including data events for PHI
  buckets), AWS Config rules for drift, GuardDuty for threat detection.
  Enable Bedrock model invocation logging to S3 or CloudWatch — without it
  you cannot reconstruct what the FM was asked or returned.
- **IAM**: Least privilege, no wildcards on PHI buckets or KMS keys.
  Separate roles for data scientists, training jobs, and inference
  endpoints. Never share a role across environments.
- **De-identification**: If the use case permits, de-identify before
  training. Document the method (Safe Harbor, Expert Determination) and
  retain the determination evidence.

Compliance decision points to surface explicitly:

- Is any input, output, prompt, or log PHI? If yes, every service in the
  path must be HIPAA-eligible and under BAA.
- Will the FM provider see PHI? Confirm the Bedrock model is in an
  eligible region and that invocation logs are encrypted with your CMK.
- Does the workload cross accounts or regions? Re-verify BAA coverage and
  data residency commitments.

## MLOps for HCLS

Clinical models decay. Assume drift and design for it:

- **Monitoring**: SageMaker Model Monitor for data quality, model quality
  (when labels arrive), and bias drift. Track feature distributions at the
  site and payer level, not only in aggregate.
- **Distribution shift sources to watch**: ICD and CPT coding updates,
  EHR template changes, new site onboarding, seasonal disease patterns,
  formulary changes, care-pathway interventions.
- **Model registry and approvals**: Every clinical model goes through the
  SageMaker Model Registry with explicit approval states. Gate promotion
  on model card completion, bias evaluation, and clinical sign-off.
- **Experimentation constraints**: Randomized online A/B testing on
  patients typically requires IRB approval. Default to shadow mode
  evaluation or champion/challenger with human-in-the-loop review.
  Document the evaluation design before enabling traffic shifts.
- **Reproducibility**: Pin container images, training data snapshots
  (S3 versioning), and hyperparameters in the registry. A model that
  cannot be rebuilt cannot be defended to regulators.
- **Incident response**: Define rollback criteria and a kill switch for
  every deployed clinical model before go-live.

## Cost Optimization

Optimize only after correctness and compliance are settled:

- **Training**: Spot instances for fault-tolerant training; checkpointing
  is mandatory — without it spot interruptions waste compute. HyperPod for
  long-running distributed jobs to amortize setup.
- **Inference shape**:
  - Real-time endpoint: latency < ~60s and payload < ~6 MB with steady
    traffic.
  - Async endpoint: large payloads (WSI, DICOM volumes, long documents)
    or long inference times.
  - Serverless inference: bursty or intermittent traffic with cold-start
    tolerance.
  - Batch transform: offline scoring of large cohorts.
- **Storage**: S3 Intelligent-Tiering for research datasets with unknown
  access patterns; lifecycle policies to Glacier for archival imaging and
  genomics data retained for compliance.
- **Bedrock**: Prefer smaller models for extraction and classification;
  reserve larger models for open-ended generation. Cache retrieval results
  where clinically safe.

## Decision Trees

Walk the user through these when the path is not obvious.

**Processing clinical text**
1. Is the task extraction, summarization, or Q&A over text? → Bedrock.
2. Is it a specialized task (custom NER schema, de-identification at
   scale, domain-specific classifier)? → SageMaker with a fine-tuned
   clinical model.
3. Is PHI involved? → Apply the Security & Compliance gates regardless of
   which service is chosen.

**Training on PHI**
1. SageMaker training job in a VPC, private subnets only.
2. Network isolation enabled on the job.
3. KMS CMK on input S3, training volume, and output artifacts.
4. BAA-covered region and services end to end.
5. No internet egress; VPC endpoints for all AWS APIs used.

**Choosing an inference pattern**
1. Latency SLO under a few seconds and payload small? → Real-time endpoint.
2. Payload large (WSI, DICOM, long report) or inference slow? → Async
   endpoint with S3 input and output.
3. Traffic bursty or low-volume? → Serverless inference.
4. Scoring a full cohort offline? → Batch transform.

**RAG over clinical or scientific content**
1. Is the content stable and well-structured? → Bedrock Knowledge Bases
   with OpenSearch Serverless.
2. Chunk by section, not fixed tokens. Preserve tables and dosing blocks.
3. Require citations in every answer; reject ungrounded responses.
4. If the corpus includes PHI, ensure the vector store, embedding model,
   and FM are all HIPAA-eligible and under BAA.

## When NOT to Use This Skill
- Non-HCLS workloads — this skill's compliance guidance (HIPAA, BAA, FDA SaMD) does not apply to general-purpose applications
- Cost estimation or pricing — use the AWS Pricing Calculator; this skill covers architecture patterns, not billing
- Reviewing or auditing an existing deployed architecture — this skill designs new systems; use Well-Architected Reviews for existing ones

## Common Mistakes

- **Wrong:** Using Bedrock for a problem that needs a custom model
  **Right:** Use SageMaker with a fine-tuned classifier when accuracy is load-bearing and the label space is narrow
  **Why:** FMs underperform well-labeled domain classifiers on constrained tasks, producing unreliable clinical outputs

- **Wrong:** Using SageMaker when Bedrock would ship in a week
  **Right:** Start with Bedrock for generic summarization or extraction tasks; move to SageMaker only when forced by accuracy, cost, or data residency
  **Why:** Building bespoke infrastructure for a commodity NLP task wastes months of engineering time

- **Wrong:** Fixed-size chunking for medical literature in RAG pipelines
  **Right:** Chunk by semantic section (abstract, methods, results, guideline recommendation) and preserve tables and dosing blocks intact
  **Why:** Fixed chunks split dosing tables, contraindications, and guideline recommendations, destroying retrieval quality

- **Wrong:** Using real-time endpoints for whole-slide images
  **Right:** Use SageMaker async endpoints for WSI and DICOM volumes
  **Why:** WSI payloads exceed real-time endpoint size limits and inference times exceed sync timeout SLOs

- **Wrong:** Forgetting to enable Bedrock invocation logging
  **Right:** Always enable Bedrock model invocation logging to S3 or CloudWatch with CMK encryption
  **Why:** Without it you cannot reconstruct what the FM was asked or returned — a compliance and debugging failure

- **Wrong:** Using public subnets or internet egress in PHI training jobs
  **Right:** Run PHI workloads in private subnets with no internet egress; use VPC endpoints for all AWS APIs
  **Why:** Violates HIPAA isolation expectations even if data itself is encrypted in transit

- **Wrong:** Using wildcard IAM policies on PHI buckets
  **Right:** Scope IAM policies to specific resources and actions; separate roles per environment and persona
  **Why:** A single over-scoped role undermines every other security control in the architecture

- **Wrong:** Training on spot instances without checkpointing
  **Right:** Always enable checkpointing when using spot instances for training jobs
  **Why:** Spot interruptions lose all progress since last checkpoint; often ends up more expensive than on-demand

- **Wrong:** Running randomized online A/B tests on patients without IRB approval
  **Right:** Default to shadow mode evaluation or champion/challenger with human-in-the-loop review
  **Why:** Randomized experiments on patients constitute human subjects research — a regulatory violation without IRB

- **Wrong:** Ignoring distribution shift until aggregate accuracy drops
  **Right:** Monitor feature distributions at the site and payer level from day one using SageMaker Model Monitor
  **Why:** By the time aggregate metrics move, site-level harm may already have occurred

- **Wrong:** Assuming de-identification removes all data handling obligations
  **Right:** Document the de-identification method (Safe Harbor or Expert Determination) and assess re-identification risk and contractual terms
  **Why:** Re-identification risk and contractual obligations often persist after de-identification

- **Wrong:** Mixing dev and prod in one AWS account with shared KMS keys
  **Right:** Separate dev and prod into distinct accounts with independent KMS keys and IAM boundaries
  **Why:** Blast radius of any mistake in the shared account covers production PHI

## When to Escalate to a Human Expert

Recommend human review when:

- The use case directly drives a treatment decision without clinician
  review in the loop.
- The workload requires FDA SaMD classification or 21 CFR Part 11 controls
  you cannot confirm.
- Data residency, cross-border transfer, or multi-jurisdiction PHI rules
  apply.
- A novel FM is being proposed for a safety-critical clinical output with
  no published evaluation on the target population.

In these cases, draft the architecture, list the open regulatory and
clinical questions, and stop before implementation.

## References

- HIPAA eligible AWS services: https://aws.amazon.com/compliance/hipaa-eligible-services-reference/
- AWS Well-Architected ML Lens: https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html
- SageMaker documentation: https://docs.aws.amazon.com/sagemaker/
- Bedrock documentation: https://docs.aws.amazon.com/bedrock/
