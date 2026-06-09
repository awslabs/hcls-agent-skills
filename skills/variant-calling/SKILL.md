---
name: variant-calling
description: Germline and somatic short-variant calling pipeline for Illumina short-read data. Use when the user mentions BWA, BWA-MEM2, GATK, HaplotypeCaller, Mutect2, VCF, GVCF, VQSR, variant calling, germline, somatic, SNV, or indel calling from FASTQ/BAM.
usage: Invoke when running germline or somatic variant calling with BWA-MEM2, GATK4 HaplotypeCaller, Mutect2, or VQSR.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {gatk: "4.5", bwa-mem2: "2.2.1", samtools: "1.19"}
tags: [skill, category:pipeline, genomics, variant-calling, gatk, bwa, hcls]
---

# Variant Calling (GATK4) — Pipeline Skill (Thin Scaffold)

## Overview

Adds decision logic for VQSR vs hard filters, WES vs WGS parameter differences, and GATK4-specific gotchas that LLMs frequently get wrong (filter thresholds, GVCF requirements, reference consistency).

## Usage

- Activate when choosing between VQSR and hard filters for a given cohort size
- Activate when setting up WES vs WGS pipeline parameters
- Activate when running Mutect2 tumor/normal or tumor-only somatic calling

## Core Concepts

## Decision Logic

```
Germline calling strategy:
├── Single sample, no future joint calling → HaplotypeCaller direct VCF
└── Cohort (≥2 samples) → HaplotypeCaller -ERC GVCF → GenomicsDBImport → GenotypeGVCFs

Filtering strategy:
├── ≥30 WGS samples OR ≥30 WES exomes → VQSR
└── <30 samples OR single sample → Hard filters

Somatic calling:
├── Tumor + matched normal → Mutect2 with both BAMs
└── Tumor-only → Mutect2 + PoN (MANDATORY) + gnomAD germline resource
```

**WES vs WGS parameter differences:**

| Step | WGS | WES |
|------|-----|-----|
| BQSR / HaplotypeCaller | No `-L` | `-L capture.bed -ip 100` |
| Known sites for BQSR | Genome-wide | Genome-wide (do NOT subset) |
| Filtering | VQSR (≥30 samples) | Hard filters unless ≥30 exomes |
| Joint genotyping intervals | Per-chromosome | `-L capture.bed` |

## Critical Parameters

**Hard filter thresholds (GATK Best Practices):**

| Filter | SNP threshold | Indel threshold |
|--------|--------------|-----------------|
| QD | < 2.0 | < 2.0 |
| FS | > 60.0 | > 200.0 |
| MQ | < 40.0 | — |
| MQRankSum | < -12.5 | — |
| ReadPosRankSum | < -8.0 | < -20.0 |
| SOR | > 3.0 | > 10.0 |

**VQSR truth sensitivity levels:**
- SNPs: 99.7
- Indels: 99.0
- Indel `--max-gaussians 4` (fewer training variants than SNPs)

**VQSR annotations:** `-an QD -an FS -an MQ -an MQRankSum -an ReadPosRankSum -an SOR`

**Mutect2 essentials:**
- `--germline-resource af-only-gnomad.hg38.vcf.gz`
- `--panel-of-normals pon.vcf.gz` (essential for tumor-only)
- `--f1r2-tar-gz` → `LearnReadOrientationModel` (FFPE/OxoG artifacts)
- `GetPileupSummaries` + `CalculateContamination` before `FilterMutectCalls`

## Common Mistakes

- **Wrong:** Aligning without proper `@RG` headers (missing ID, SM, PL, LB)
  **Right:** Always specify at alignment: `-R '@RG\tID:x\tSM:x\tPL:ILLUMINA\tLB:x'`
  **Why:** GATK refuses to run or silently merges samples when SM tags are wrong

- **Wrong:** Running HaplotypeCaller without `-ERC GVCF` for cohort analysis
  **Right:** Always produce GVCFs when joint genotyping will be performed
  **Why:** Regular VCFs cannot be joint-genotyped; must re-call from BAM

- **Wrong:** Reusing SNP hard-filter thresholds for indels (e.g., `FS > 60` for indels)
  **Right:** Use `FS > 200` for indels, `FS > 60` for SNPs
  **Why:** Indels tolerate higher strand bias; SNP thresholds over-filter real indels

- **Wrong:** Applying VQSR to <30 samples
  **Right:** Use hard filters for small cohorts
  **Why:** VQSR needs many variants to train its Gaussian mixture model

- **Wrong:** Subsetting `--known-sites` VCFs to WES capture BED for BQSR
  **Right:** Use genome-wide known-sites; only restrict analysis intervals via `-L`
  **Why:** BQSR needs genome-wide known sites to model base quality errors

- **Wrong:** Skipping `samtools index` between GATK steps
  **Right:** Index after every BAM-producing step
  **Why:** GATK requires BAM indices; missing them causes immediate failure

- **Wrong:** Mixing reference files from different genome builds
  **Right:** Ensure ref.dict, ref.fa.fai, BWA index, and all VCFs match the same build
  **Why:** Mismatched dictionaries cause silent failures or cryptic errors

- **Wrong:** Running Mutect2 tumor-only without a panel of normals
  **Right:** Always provide `--panel-of-normals` for tumor-only calling
  **Why:** Without PoN, recurrent sequencing artifacts are called as somatic mutations

## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation
